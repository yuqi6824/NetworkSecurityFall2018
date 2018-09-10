#！/usr/bin/env python
#coding:utf-8

import asyncio

base = 'echo_message_'
counter = 0

def increment():
    global counter
    counter = counter + 1 
    return counter

async def echo_server(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))
    
    #Create file
    i = increment()
    file_name = base + str(i)
    file = open(file_name, 'w')
    file.write(message)
    file.close()
    
    print("Send: %r" % message)
    print("echo_message has been saved")
    writer.write(data)
    await writer.drain()
    if message == '_EXIT_':
        print("Close the client socket")
        writer.close()

loop = asyncio.get_event_loop()
coro = asyncio.start_server(echo_server, '127.0.0.1', 8000, loop=loop)
server = loop.run_until_complete(coro)

print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()