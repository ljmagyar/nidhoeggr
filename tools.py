from sys import stderr
from time import time, ctime
from threading import Thread, Event

class Log: # {{{
	"""
	"""
	DEBUG=0
	INFO=1
	WARNING=2
	ERROR=3

	_loglevelrepr = ['#','*','>','!']

	def __init__(self,filename=None):
		"""
		"""
		if filename==None:
			self.out_fh = stderr
		else:
			self.out_fh = open(filename,'a')
		self.setLogLevel(Log.INFO)

	def log(self,loglevel,msg):
		"""
		"""
		if loglevel >= self._loglevel:
			message = "%s %s:\t%s" % (Log._loglevelrepr[loglevel],ctime(),msg)
			print >>self.out_fh, message

	def setLogLevel(self,loglevel):
		"""
		"""
		self._loglevel = loglevel

	def __call__(self,loglevel,msg):
		"""
		"""
		self.log(loglevel,msg)

# }}}

class IdleWatcher: # {{{
	"""
	"""
	def __init__(self,timeout):
		"""
		"""
		self.params['timeout'] = timeout
		self.setActive()
	
	def setActive(self):
		"""
		"""
		self.params['lastactivity'] = time()

	def checkTimeout(self,currenttime=None,timeout=None):
		"""
		"""
		if currenttime is None:
			currenttime = time()
		if timeout is None:
			timeout = self.params['timeout']
		return self.params['lastactivity'] + timeout < currenttime


# IdleWatcher }}}

class StopableThread(Thread): # {{{
	"""
	"""
	def __init__(self,sleep=0):
		"""
		"""
		Thread.__init__(self)
		self._stopevent = Event()
		self._sleep = sleep

	def join(self,timeout=None):
		"""
		initiate a graceful shutdown of the cleaning thread
		"""
		self._stopevent.set()
		self._join()
		Thread.join(self,timeout)

	def run(self):
		while not self._stopevent.isSet():
			self._run()
			if self._sleep>0:
				self._stopevent.wait(self._sleep)

	def _join(self):pass

	def _run(self):pass

# }}}

if __name__=="__main__": pass

log = Log()
if __debug__:
	log.setLogLevel(Log.DEBUG)

# vim:fdm=marker
