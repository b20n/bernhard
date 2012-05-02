# -*- coding: utf-8 -

import socket
import struct

import pb

class TransportError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class TCPTransport(object):
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def close(self):
        self.sock.close()

    def write(self, message):
        try:
            # Tx length header
            self.sock.send(struct.pack('!I', len(message)))
            # Tx message
            self.sock.send(message)
            # Rx length header
            rxlen = struct.unpack('!I', self.sock.recv(4))[0]
            # Rx response
            return self.sock.recv(rxlen)
        except (socket.error, struct.error), e:
            raise TransportError(str(e))


class UDPTransport(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def close(self):
        self.sock.close()

    def write(self, message):
        try:
            self.sock.sendto(message, (self.host, self.port))
        except socket.error, e:
            raise TransportError(str(e))


class Event(object):
    def __init__(self, event=None, params=None):
        if event:
            self.event = event
        elif params:
            self.event = pb.Event()
            for key, value in params.iteritems():
                setattr(self, key, value)
        else:
            self.event = pb.Event()

    def __getattr__(self, name):
        if name == 'metric':
            name = 'metric_f'
        if name in set(f.name for f in pb.Event.DESCRIPTOR.fields):
            return getattr(self.event, name)

    def __setattr__(self, name, value):
        if name == 'metric':
            name = 'metric_f'
        if name in set(f.name for f in pb.Event.DESCRIPTOR.fields):
            object.__setattr__(self.event, name, value)
        else:
            object.__setattr__(self, name, value)


class Message(object):
    def __init__(self, message=None, events=None, raw=None, query=None):
        if raw:
            self.message = pb.Msg().FromString(raw)
        elif message:
            self.message = message
        elif events:
            self.message = pb.Msg()
            self.message.events.extend([e.event for e in events])
        elif query:
            self.message = pb.Msg()
            self.message.query.string = str(query)
        else:
            self.message = pb.Msg()

    def __getattr__(self, name):
        if name in set(f.name for f in pb.Msg.DESCRIPTOR.fields):
            return getattr(self.message, name)

    def __setattr__(self, name, value):
        if name in set(f.name for f in pb.Msg.DESCRIPTOR.fields):
            object.__setattr__(self.message, name, value)
        else:
            object.__setattr__(self, name, value)

    # Special-case the `events` field so we get boxed objects
    @property
    def events(self):
        return [Event(event=e) for e in self.message.events]

    @property
    def raw(self):
        return self.message.SerializeToString()


class Client(object):
    def __init__(self, host='127.0.0.1', port=5555, transport=TCPTransport):
        self.host = host
        self.port = port
        self.transport = transport
        self.connect()

    def connect(self):
        self.connection = self.transport(self.host, self.port)

    def reconnect(self):
        try:
            self.connection.close()
        except:
            pass
        self.connect()

    def transmit(self, message):
        for i in xrange(2):
            try:
                raw = self.connection.write(message.raw)
                return Message(raw=raw)
            except TransportError:
                self.reconnect()
        return Message()

    def send(self, event):
        message = Message(events=[Event(params=event)])
        response = self.transmit(message)
        return response.ok

    def query(self, q):
        message = Message(query=q)
        response = self.transmit(message)
        return response.events
