import asyncio

class Timer():
	def __init__(self, timeout, callback, pkt, loop):
		self.timeout = timeout
		self.callback = callback
		self.pkt = pkt
		self.loop = loop
		self.task = self.loop.call_later(timeout, self.callback, self.pkt)
		
	def cancel(self):
		self.task.cancel()

class shutdown():
	def __init__(self, timeout, callback, loop):
		self.timeout = timeout
		self.callback = callback
		self.loop = loop
		self.task = self.loop.call_later(timeout, self.callback)
		
	def cancel(self):
		self.task.cancel()

'''class AckTimer(object):
	def __init__(self, timeout, callback, loop):
		self.timeout = timeout
		self.callback = callback
		self.loop = loop
		self.loop = self.loop.call_later(timeout, self.callback)'''

class PopTimer():
	def __init__(self, timeout, callback, loop):
		self.timeout = timeout
		self.callback = callback
		self.loop = loop
		self.task = self.loop.call_later(timeout, self.callback)

	
			
			
		