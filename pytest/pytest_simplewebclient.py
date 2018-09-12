#！/usr/bin/env python
#coding:utf-8

import asyncio
import sys
import time
import datetime

base = 'web_response_'
counter = 0

def increment():
    global counter
    counter = counter + 1 
    return counter

async def echo_client(message, loop, port):
    reader, writer = await asyncio.open_connection('127.0.0.1', port,
                                                   loop=loop)

    print('Send: %r' % message)
    writer.write(message.encode())
    data = await reader.read(10000)
    print('Received: %r' % data.decode())
    print('response_message has been saved')

    # Create files
    i = increment()
    file_name = base + str(i)
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    file = open(file_name, 'w')
    file.write(st + '\n')
    file.write(message + '\n')
    file.write(data.decode())
    file.close()

    if message == '_EXIT_':
        print('Close the socket')
        writer.close()

def main(port):
    while(True):
        message = input("Please input path and name of file:")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(echo_client(message, loop, port))
        if message == '_EXIT_':
            break
    loop.close()

if __name__ == '__main__':
    main(*sys.argv[1:2])