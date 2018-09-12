#！/usr/bin/env python
#coding:utf-8

import asyncio
import sys
import datetime
import time

base = 'security_message_'
counter = 0

def increment():
    global counter
    counter = counter + 1 
    return counter

def encrypt(message):
    plaintext = message
    cipher = ''
    for each in plaintext:
        c = (ord(each)+3) % 126
        if c < 32: 
            c+=31
        cipher += chr(c)
    return cipher

def decrypt(message):
    cipher = message
    plaintext = ''
    for each in cipher:
        p = (ord(each)-3) % 126
        if p < 32:
            p+=95
        plaintext += chr(p)
    return plaintext

async def secure_server(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))

    #Judge encry or decry
    if 'encrypt' in message:
        response = 'cipher,'+encrypt(message[8:])
        print("Send: %r" %response)
        writer.write(response.encode())
    elif 'decrypt' in message:
        response = 'plaintext,'+decrypt(message[8:])
        print("Send: %r" %response)
        writer.write(response.encode())
    else:
        response = 'error input'
        print("Send: error input")
        writer.write(response.encode())
    
    #Create file
    i = increment()
    file_name = base + str(i)
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    file = open(file_name, 'w')
    file.write(st + '\n')
    file.write(message + '\n')
    file.write(response)
    file.close()
    
    #print("Send: %r" % message)
    print("Secure_message has been saved")
    #writer.write(data)
    await writer.drain()
    if message == '_EXIT_':
        print("Close the socket")
        writer.close()

def main(port):
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(secure_server, '127.0.0.1', port, loop=loop)
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