#！/usr/bin/env python
#coding:utf-8
import asyncio


async def echo_client(message, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8000,
                                                   loop=loop)

    print('Send: %r' % message)
    writer.write(message.encode())

    data = await reader.read(100)
    print('Received: %r' % data.decode())
    print('response_message has been saved')

    if data.decode() == '_EXIT_':
        print('Close the socket')
        writer.close()
i = 1
base = 'response_message_'
while(True):
    message = input('Please enter your massage:')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(echo_client(message, loop))
    # Create files
    file_name = base + str(i)
    i = i + 1
    file = open(file_name, 'w')
    file.write(message)
    if message == '_EXIT_':
        break
loop.close()