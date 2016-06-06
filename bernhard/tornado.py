from __future__ import absolute_import

import socket
import struct
from collections import deque

from . import log, Message, Event

from tornado import gen, iostream, ioloop, concurrent, locks


class AsyncTCPClient(object):
    def __init__(self, host='127.0.0.1', port=5555, loop=None):
        self.host = host
        self.port = port
        self.loop = loop or ioloop.IOLoop.current()
        self.futures = deque()
        self.connection = None
        self.connect_lock = locks.Lock()

    @gen.coroutine
    def connect(self):
        with (yield self.connect_lock.acquire()):
            if self.connection is not None:
                raise gen.Return(self)

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            connection = iostream.IOStream(s)
            yield connection.connect((self.host, self.port))
            self.connection = connection
            self.loop.spawn_callback(self.read_loop)
            raise gen.Return(self)

    @gen.coroutine
    def read_loop(self):
        while self.connection:
            try:
                header = yield self.connection.read_bytes(4)
            except (IOError, socket.error) as e:
                self.disconnect(e)
                raise
            else:
                rxlen = struct.unpack('!I', header)[0]
                raw = yield self.connection.read_bytes(rxlen)
                future = self.futures.popleft()
                future.set_result(raw)

    def disconnect(self, exc):
        try:
            self.connection.close()
        except (IOError, socket.error):
            log.exception("Exception disconnecting client")
        finally:
            self.connection = None
            for future in self.futures:
                future.set_exception(exc)

    @gen.coroutine
    def transmit(self, message):
        if self.connection is None:
            raise IOError('Not connected')
        try:
            raw = message.raw
            frame = struct.pack('!I', len(raw)) + raw
            self.connection.write(frame)
            future = concurrent.Future()
            self.futures.append(future)
            raw = yield future
            raise gen.Return(Message(raw=raw))
        except (IOError, socket.error, iostream.StreamBufferFullError) as e:
            self.disconnect(e)
            raise

    @gen.coroutine
    def send(self, *events):
        message = Message(events=[Event(params=event) for event in events])
        response = yield self.transmit(message)
        raise gen.Return(response.ok)

    @gen.coroutine
    def query(self, q):
        message = Message(query=q)
        response = yield self.transmit(message)
        raise gen.Return(response.events)


class BufferedClient(object):
    def __init__(self, host='127.0.0.1', port=5555, send_interval=1.0,
                 reconnect_timeout=1.0, max_queue_size=2000, loop=None):
        self.host = host
        self.port = port
        self.loop = loop or ioloop.IOLoop.current()
        self.reconnect_timeout = reconnect_timeout
        self.send_interval = send_interval
        self.max_queue_size = max_queue_size
        self.queue = deque(maxlen=self.max_queue_size)
        self.loop.spawn_callback(self.send_loop)

    @gen.coroutine
    def send_loop(self):
        client = AsyncTCPClient(self.host, self.port, loop=self.loop)
        while True:
            try:
                if client.connection is None:
                    yield client.connect()
                if len(self.queue) > 0:
                    futures = [client.transmit(message) for message in self.queue]
                    self.queue = deque(maxlen=self.max_queue_size)
                    yield futures
            except (IOError, socket.error, iostream.StreamBufferFullError):
                yield gen.sleep(self.reconnect_timeout)
            else:
                yield gen.sleep(self.send_interval)

    def send(self, *events):
        message = Message(events=[Event(params=event) for event in events])
        self.queue.append(message)
