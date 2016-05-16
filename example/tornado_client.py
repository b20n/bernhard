from bernhard.tornado import BufferedClient, AsyncTCPClient
from tornado.ioloop import IOLoop
from tornado.gen import coroutine, sleep
loop = IOLoop.current()

c = loop.run_sync(lambda: AsyncTCPClient().connect())
print loop.run_sync(lambda: c.send({'host': 'localhost', 'service': 'test'}))


@coroutine
def send():
    c = BufferedClient()
    c.send({'host': 'localhost', 'service': 'buffer test'})
    yield sleep(0.5)
    c.send({'host': 'localhost', 'service': 'buffer test'})
    c.send({'host': 'localhost', 'service': 'buffer test'})
    yield sleep(1.5)

loop.run_sync(send)
