#！/usr/bin/env python
#coding:utf-8

import asyncio
import random
import time
import datetime

base = '8ball_message_'
counter = 0
dic = {}
ls = ['Your guess is as good as mine.', 'You need a vacation.', 'It\'s Trump\'s fault!', 'I don\'t know. What do you think?', 'Nobody ever said it would be easy, they only said it would be worth it.', 'You really expect me to answer that?', 'You\'re going to get what you deserve.', 'That depends on how much you\'re willing to pay.']

def increment():
    global counter
    counter = counter + 1 
    return counter

async def ball_server(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))

    #Judge if the message from client in track
    if message in dic:
        response = dic.get(message)
        print("Send: %r" %response)
        writer.write(response.encode())
    else:
        response = random.choice(ls)
        dic[message] = response
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
    print("message has been saved")
    writer.write(data)
    await writer.drain()
    if message == '_EXIT_':
        print("Close the client socket")
        writer.close()

loop = asyncio.get_event_loop()
coro = asyncio.start_server(ball_server, '127.0.0.1', 8000, loop=loop)
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