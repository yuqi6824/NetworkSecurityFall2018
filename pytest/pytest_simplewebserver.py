#！/usr/bin/env python
#coding:utf-8

import asyncio
import sys
import datetime
import os
import time

base = 'web_message_'
counter = 0

def increment():
    global counter
    counter = counter + 1 
    return counter

def search(complete_path):
    path, name = os.path.split(complete_path)
    for root, dirs, files in os.walk(path):
        if name in dirs or name in files:
            flag = 1
            root = str(root)
            dirs = str(dirs)
            return True
    return False

async def http_server(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))

    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    
    if search(message):
        with open(message, 'rb') as f:
            contents = f.read()
        response = 'HTTP/1.1 200 OK ' + st + ' ' + str(contents)
        writer.write(response.encode())
    else:
        response = 'HTTP/1.1 404 NOT FOUND ' + st
        writer.write(response.encode())
    #Create file
    i = increment()
    file_name = base + str(i)
    file = open(file_name, 'w')
    file.write(st + '\n')
    file.write(message + '\n')
    file.write(response)
    file.close()
    print("Send: %r" % response)
    print("server_message has been saved")
    #writer.write(data)
    await writer.drain()
    if message == '_EXIT_':
        print("Close the socket")
        writer.close()

def main(port):
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(http_server, '127.0.0.1', port, loop=loop)
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

if __name__ == '__main__':
    main(*sys.argv[1:])