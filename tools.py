import sys
import time
import threading

class Log: # {{{
	"""
	"""
	DEBUG=0
	INFO=1
	WARNING=2
	ERROR=3

	_loglevelrepr = ['#','*','>','!']

	def __init__(self):
		"""
		"""
		self.setLogLevel(Log.INFO)

	def log(self,loglevel,msg):
		"""
		"""
		if loglevel >= self._loglevel:
			message = "%s %s:\t%s" % (Log._loglevelrepr[loglevel],time.ctime(),msg)
			print >>sys.stderr, message

	def setLogLevel(self,loglevel):
		"""
		"""
		self._loglevel = loglevel

	def __call__(self,loglevel,msg):
		"""
		"""
		self.log(loglevel,msg)

log = Log()
if __debug__:
	log.setLogLevel(Log.DEBUG)

# }}}

class ReadWriteLock: # {{{
	"""
	"""

	def __init__(self):
		"""
		"""
		self._read_ready = threading.Condition(threading.Lock())
		self._readers = 0

	def acquire_read(self):
		"""
		"""
		self._read_ready.acquire()
		try: self._readers += 1
		finally: self._read_ready.release()

	def release_read(self):
		"""
		"""
		self._read_ready.acquire()
		try:
			self._readers -= 1
			if not self._readers:
				self._read_ready.notifyAll()
		finally:
			self._read_ready.release()
	
	def acquire_write(self):
		"""
		"""
		self._read_ready.acquire()
		while self._readers > 0:
			self._read_ready.wait()
	
	def release_write(self):
		"""
		"""
		self._read_ready.release()

# }}}

class IdleWatcher: # {{{
	"""
	"""
	def __init__(self,timeout):
		"""
		"""
		self._timeout = timeout
		self.setActive()
	
	def setActive(self):
		"""
		"""
		self._lastactivity = time.time()

	def checkTimeout(self,currenttime=time.time()):
		"""
		"""
		return self._lastactivity + self._timeout < currenttime

# IdleWatcher }}}

class StopableThread(threading.Thread): # {{{
	"""
	"""
	def __init__(self,sleep=0):
		"""
		"""
		threading.Thread.__init__(self)
		self._stopevent = threading.Event()
		self._sleep = sleep

	def join(self,timeout=None):
		"""
		initiate a graceful shutdown of the cleaning thread
		"""
		self._join()
		self._stopevent.set()
		threading.Thread.join(self,timeout)

	def run(self):
		while not self._stopevent.isSet():
			self._run()
			if self._sleep>0:
				self._stopevent.wait(self._sleep)

	def _join(self):pass
	def _run(self):pass

# }}}

# vim:fdm=marker
