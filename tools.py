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

	def __init__(self,filename=None):
		"""
		"""
		if filename==None:
			self.out_fh = sys.stderr
		else:
			self.out_fh = open(filename,'a')
		self.setLogLevel(Log.INFO)

	def log(self,loglevel,msg):
		"""
		"""
		if loglevel >= self._loglevel:
			message = "%s %s:\t%s" % (Log._loglevelrepr[loglevel],time.ctime(),msg)
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
		try: 
			self._readers += 1
		finally: 
			self._read_ready.release()

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
		self.params['timeout'] = timeout
		self.setActive()
	
	def setActive(self):
		"""
		"""
		self.params['lastactivity'] = time.time()

	def checkTimeout(self,currenttime=None):
		"""
		"""
		if currenttime is None:
			currenttime = time.time()
		return self.params['lastactivity'] + self.params['timeout'] < currenttime


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
		self._stopevent.set()
		self._join()
		threading.Thread.join(self,timeout)

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
