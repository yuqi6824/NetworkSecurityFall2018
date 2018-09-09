#！/usr/bin/env python    
#coding:utf-8
import asyncio

async def echo_server(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))

    print("Send: %r" % message)
    writer.write(data)
    await writer.drain()

    if message == '_EXIT_':
        print("Close the client socket")
        writer.close()

loop = asyncio.get_event_loop()
coro = asyncio.start_server(echo_server, '127.0.0.1', 8000, loop=loop)
#print(coro)
server = loop.run_until_complete(coro)
#print(server)

print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()