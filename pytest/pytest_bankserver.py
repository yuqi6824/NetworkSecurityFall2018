#！/usr/bin/env python
#coding:utf-8

import asyncio
import time
import datetime

base = 'bank_message_'
counter = 0
balance = 0

def increment():
    global counter
    counter = counter + 1 
    return counter

def changeBalance(amount):
    global balance
    balance = balance + amount
    if (balance < 0):
        balance = 0
    return balance

async def bank_server(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))

    #Response to different operations
    if message == 'balance':
        response = str(changeBalance(0))
        print("Send: %r" %response)
        writer.write(response.encode())
    elif 'deposit' in message:
        balance = changeBalance(int(message[8:]))
        response = str(balance)
        print("Send: %r" %response)
        writer.write(str(response).encode())
    elif 'withdraw' in message:
        if (changeBalance(0) - float(message[8:])) > 0:
            changeBalance(float((-1) * float(message[8:])))
            response = message[8:]
            print("Send: %r" %response)
        else:
            response = str(changeBalance(0))
            changeBalance(changeBalance(0))
            print("Send: %r" %response)
        writer.write(str(response).encode())
    else:
        response = 'error input'
        print("Send: %r" %response)
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
    print("bank_message has been saved")
    writer.write(data)
    await writer.drain()
    if message == '_EXIT_':
        print("Close the client socket")
        writer.close()

loop = asyncio.get_event_loop()
coro = asyncio.start_server(bank_server, '127.0.0.1', 8000, loop=loop)
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