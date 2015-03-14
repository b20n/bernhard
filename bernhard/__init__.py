# -*- coding: utf-8 -

import logging
log = logging.getLogger(__name__)

import socket
import ssl
import struct
import sys
import os

from . import pb

string_type = str
if sys.version_info[1] < 3:
    string_type = basestring

class TransportError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class TCPTransport(object):
    def __init__(self, host, port):
        for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                log.debug("Creating socket with %s %s %s", af, socktype, proto)
                self.sock = socket.socket(af, socktype, proto)
                self.sock.settimeout(15.0)
            except socket.error as e:
                log.exception("Exception creating TCP socket: %s", e)
                self.sock = None
                continue
            try:
                self.sock.connect(sa)
            except socket.error as e:
                log.exception("Exception connecting to TCP socket: %s", e)
                self.sock.close()
                self.sock = None
                continue
            break
        if self.sock is None:
            raise TransportError("Could not open TCP socket.")

    def close(self):
        self.sock.close()

    def read_exactly(self, sock, size):
        buffer = ''
        while len(buffer) < size:
            data = sock.recv(size - len(buffer))
            if not data:
                log.debug("Expected to read %s bytes, but read %s bytes", size, len(buffer))
                break
            buffer += data
        return buffer

    def write(self, message):
        try:
            # Tx length header and message
            log.debug("Sending event to Riemann")
            self.sock.sendall(struct.pack('!I', len(message)) + message)

            # Rx length header
            log.debug("Reading Riemann Response Length Header")
            response = self.read_exactly(self.sock, 4)
            rxlen = struct.unpack('!I', response)[0]
            log.debug("Header Length Is: %d", rxlen)

            # Rx entire response
            log.debug("Reading Riemann Response")
            response = self.read_exactly(self.sock, rxlen)

            return response
        except (socket.error, struct.error) as e:
            log.exception("Exception sending event to Riemann over TCP socket: %s", e)
            raise TransportError(str(e))


class SSLTransport(TCPTransport):
    def __init__(self, host, port, keyfile=None, certfile=None, ca_certs=None):
        log.debug("Using SSL Transport")

        TCPTransport.__init__(self, host, port)

        self.sock = ssl.wrap_socket(self.sock,
                                    keyfile=keyfile,
                                    certfile=certfile,
                                    cert_reqs=ssl.CERT_REQUIRED,
                                    ssl_version=ssl.PROTOCOL_TLSv1,
                                    ca_certs=ca_certs)


class UDPTransport(object):
    def __init__(self, host, port):
        log.debug("Using UDP Transport")

        self.host = None
        self.port = None
        for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_DGRAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                self.host = sa[0]
                self.port = sa[1]
            except socket.error as e:
                log.exception("Exception opening socket: %s", e)
                self.sock = None
                continue
            break
        if self.sock is None:
            raise TransportError("Could not open socket.")

    def close(self):
        self.sock.close()

    def write(self, message):
        try:
            self.sock.sendto(message, (self.host, self.port))
        except socket.error as e:
            log.exception("Exception writing to socket: %s", e)
            raise TransportError(str(e))


class Event(object):
    def __init__(self, event=None, params=None):
        if event:
            self.event = event
        elif params:
            self.event = pb.Event()
            for key, value in params.items():
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
        if name == 'tags':
            self.event.tags.extend(value)
        elif name == 'attributes':
            if type(value) == dict:
                for key, val in value.items():
                    a = self.event.attributes.add()
                    a.key = key
                    if isinstance(val, bytes):
                        val = val.decode('utf-8')
                    elif not isinstance(val, string_type):
                        val = string_type(val)
                    a.value = string_type(val)
            else:
                raise TypeError("'attributes' parameter must be type 'dict'")
        elif name in set(f.name for f in pb.Event.DESCRIPTOR.fields):
            object.__setattr__(self.event, name, value)
        else:
            object.__setattr__(self, name, value)

    def __str__(self):
        return str(self.event)


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
        self.connection = None

    def connect(self):
        self.connection = self.transport(self.host, self.port)

    def disconnect(self):
        try:
            self.connection.close()
        except Exception as e:
            log.exception("Exception disconnecting client: %s", e)
            pass
        self.connection = None

    def transmit(self, message):
        for i in range(2):
            if not self.connection:
                self.connect()
            try:
                raw = self.connection.write(message.raw)
                return Message(raw=raw)
            except TransportError:
                self.disconnect()
        return Message()

    def send(self, event):
        message = Message(events=[Event(params=event)])
        response = self.transmit(message)
        return response.ok

    def query(self, q):
        message = Message(query=q)
        response = self.transmit(message)
        return response.events


class SSLClient(Client):
    def __init__(self, host='127.0.0.1', port=5554,
                 keyfile=None, certfile=None, ca_certs=None):
        Client.__init__(self, host=host, port=port, transport=SSLTransport)

        self.keyfile = keyfile
        self.certfile = certfile
        self.ca_certs = ca_certs

    def connect(self):
        self.connection = self.transport(self.host, self.port, self.keyfile,
                                         self.certfile, self.ca_certs)
