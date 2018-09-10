#！/usr/bin/env python
#coding:utf-8

import asyncio
import time
import datetime

base = 'bank_response_'
counter = 0

def increment():
  global counter
  counter = counter + 1 
  return counter

async def bank_client(message, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8000,
                                                   loop=loop)

    print('Send: %r' % message)
    writer.write(message.encode())
    data = await reader.read(100)
    if message == 'balance':
    	print('The balance is %f' % float(data.decode()))
    elif 'deposit' in message:
    	print('Ok, your current balance is %f' % float(data.decode()))
    elif 'withdraw' in message:
    	print('You have withdrawed %f' %float(data.decode()))
    else:
    	print('Received: %r' % data.decode())
    print('response_message has been saved')

    # Create files
    massage = data.decode()
    i = increment()
    file_name = base + str(i)
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    response = data.decode()
    file = open(file_name, 'w')
    file.write(st + '\n')
    file.write(message + '\n')
    file.write(response)
    file.close()

    if message == '_EXIT_':
    	print('Close the socket')
    	writer.close()

print('Please enter this operations'+'\n'+'balance'+'\n'+'deposit n'+'\n'+'withdraw n')
while(True):
	message = input('Please enter your massage:')
	loop = asyncio.get_event_loop()
	loop.run_until_complete(bank_client(message, loop))
	if message == '_EXIT_':
		break
loop.close()