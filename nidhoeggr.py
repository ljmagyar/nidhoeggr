#!/usr/bin/env python2.2

SERVER_VERSION="nidhoeggr $Id: nidhoeggr.py,v 1.1 2003/04/24 23:36:03 ridcully Exp $"

copyright = """
Copyright 2003 Christoph Frick <rid@gmx.net>
Copyright 2003 GPLOP Development Group
All Rights Reserved
This software is the proprietary information of the GPLOP Development Group
Use is subject to license terms
"""

import sys
import sha
import zlib
import struct
import time
import SocketServer
import random
import string
import threading
import cPickle

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
			print "%s %s:\t%s" % (Log._loglevelrepr[loglevel],time.ctime(),msg)

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

class CleanUp: # {{{
	"""
	"""
	def __init__(self,timeout=3600.0):
		"""
		"""
		self.timeout = timeout * 1000
		self.setActive()
	
	def setActive(self):
		"""
		"""
		self.lastactivity = time.time()

	def checkTimeout(self):
		"""
		"""
		return self.lastactivity + self.timeout < time.time()

# CleanUp }}}

class RaceList(threading.Thread): # {{{
	"""
	"""

	CLEANINTERVAL = 60.0 # seconds

	def __init__(self):
		"""
		"""
		threading.Thread.__init__(self)

		self._stopevent = threading.Event()

		self._users = {}
		self._users_by_uniqid = {}
		self._races = {}
		self._reqfull = []

		self._users_rwlock = ReadWriteLock()
		self._races_rwlock = ReadWriteLock()

		self._load()

	def addUser(self,user):
		"""
		"""
		self._users_rwlock.acquire_write()
		try:
			if not self._users.has_key(user.client_id):
				self._users[user.client_id] = user
				self._users_by_uniqid[user.client_uniqid] = user
			else:
				raise RaceListProtocolException("user already registered")
		finally:
			self._users_rwlock.release_write()

	def getUser(self,client_id):
		"""
		"""
		self._users_rwlock.acquire_read()
		try:
			if not self._users.has_key(client_id):
				raise RaceListProtocolException("user unknown/not logged in")
			ret = self._users[client_id]
			ret.setActive()
		finally:
			self._users_rwlock.release_read()
		return ret

	def getUserByUniqId(self,client_uniqid):
		"""
		"""
		if self._users_by_uniqid.has_key(client_uniqid):
			return self._users_by_uniqid[client_uniqid]
		return None

	def addRace(self,race):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			if not self._races.has_key(race.server_id):
				self._races[race.server_id] = race
			else:
				raise RaceListProtocolException("race already registered")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()

	def removeRace(self,server_id):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			if self._races.has_key(server_id):
				del self._races[server_id]
			else:
				raise RaceListProtocolException("unknown server_id")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()
	
	def driverJoinRace(self,server_id,driver):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			if self._races.has_key(server_id):
				self._races[server_id].addDriver(driver)
			else:
				raise RaceListProtocolException("unknown server_id")
			for race in self._races.values():
				race.removeDriver(driver.client_id)
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()
	
	def driverLeaveRace(self,server_id,client_id):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			if self._races.has_key(server_id):
				self._races[server_id].removeDriver(client_id)
			else:
				raise RaceListProtocolException("unknown server_id")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()

	def _buildRaceListAsReply(self):
		"""
		"""
		self.reqfull = []
		for race in self._races.values():
			self.reqfull.append(race.getRaceAsReply())
			for driver in race.drivers.values():
				self.reqfull.append(driver.getDriverAsReply())

	def getRaceListAsReply(self):
		"""
		"""
		ret = []
		self._races_rwlock.acquire_read()
		try:
			ret = self.reqfull
		finally:
			self._races_rwlock.release_read()
		return ret

	def run(self):
		"""
		lurks behind the scenes and cleans the._races and the._users
		"""
		while not self._stopevent.isSet():
			for user in self._users.keys():
				if self._users[user].checkTimeout():
					if __debug__:
						log(Log.DEBUG, "removing user %s" % user )
					del self._users[user]

			for race in self._races.keys():
				if self._races[race].checkTimeout():
					if __debug__:
						log(Log.DEBUG, "removing race %s" % race )
					self.removeRace(self._races[race].server_id)

			self._stopevent.wait(RaceList.CLEANINTERVAL)

	def join(self,timeout=None):
		"""
		initiate a graceful shutdown of the cleaning thread
		"""
		self._store()
		self._stopevent.set()
		threading.Thread.join(self,timeout)

	def _store(self,filename='racelist.cpickle'):
		"""
		stores the current racelist in the given file
		"""
		log(Log.INFO, "store racelist to file '%s'" % filename )
		try:
			outf = open(filename, "w")
			cPickle.dump(self._users, outf)
			cPickle.dump(self._races, outf)
			outf.close()
		except Exception, e:
			log(Log.WARNING,"failed to save racelist state to file '%s': %s" % (filename,e) )

	def _load(self,filename='racelist.cpickle'):
		"""
		loads the racelist from the given file
		"""
		log(Log.INFO, "load racelist from file '%s'" % filename )
		try:
			inf = open(filename, "r")
			self._users = cPickle.load(inf)
			self._races = cPickle.load(inf)
			inf.close()
			self._users_by_uniqid = {}
			for user in self._users.values():
				self._users_by_uniqid[user.client_uniqid] = user
		except Exception,e:
			log(Log.WARNING, "failed to load racelist state from file '%s': %s" % (filename, e) )

# }}}

class Race(CleanUp): # {{{
	"""
	"""
	
	def __init__(self,params):
		"""
		"""
		self.params = params
		self.params["server_id"] = sha.new("%s%s%s%s%s" % (self.client_id,self.ip, self.joinport, time.time(), random.randint(0,1000000))).hexdigest()
		self.params["sessionleft"] = self.praclength
		self.params["sessiontype"] = 0
		
		self.drivers = {}

		self._initstateless()

	def _initstateless(self):
		CleanUp.__init__(self,900.0)
		self._rwlock = ReadWriteLock()

	def addDriver(self,driver):
		"""
		"""
		self.setActive()
		self._rwlock.acquire_write()
		try:
			if not self.drivers.has_key(driver.client_id):
				self.drivers[driver.client_id] = driver
			# silently ignore the request, if this driver has already joined the race
		finally:
			self._rwlock.release_write()

	def removeDriver(self,client_id):
		"""
		"""
		self.setActive()
		self._rwlock.acquire_write()
		try:
			if self.drivers.has_key(client_id):
				del self.drivers[client_id]
			# silently ignore the request, if there is not driver with this id in the race
		finally:
			self._rwlock.release_write()

	def getRaceAsReply(self):
		"""
		"""
		self._rwlock.acquire_read()
		ret = (
			"R",
			str(self.server_id),
			str(self.ip),
			str(self.joinport),
			str(self.name),
			str(self.info1),
			str(self.info2),
			str(self.comment),
			str(self.isdedicatedserver),
			str(self.ispassworded),
			str(self.isbosspassworded),
			str(self.isauthenticedserver),
			str(self.allowedchassis),
			str(self.allowedcarclasses),
			str(self.allowsengineswapping),
			str(self.modindent),
			str(self.maxlatency),
			str(self.bandwidth),
			str(self.maxplayers),
			str(self.trackdir),
			str(self.racetype),
			str(self.praclength),
			str(self.sessionleft),
			str(self.sessiontype)
		)
		self._rwlock.release_read()
		return ret

	def __getattr__(self,name):
		"""
		"""
		if self.params.has_key(name):
			return self.params[name]
		if hasattr(self,name):
			return getattr(self,name)
		raise AttributeError, "No such attribute: "+name

	def __getstate__(self):
		"""
		"""
		return (self.params,self.drivers)
	
	def __setstate__(self,data):
		"""
		"""
		(self.params, self.drivers) = data
		self._initstateless()
			
# }}}

class User(CleanUp): # {{{
	"""
	"""

	def __init__(self,client_uniqid,outsideip):
		"""
		"""
		CleanUp.__init__(self)

		self.client_uniqid = client_uniqid
		self.outsideip = outsideip
		self.client_id = sha.new("%s%s%s" % (self.client_uniqid, time.time(), random.randint(0,1000000))).hexdigest()
# }}}

class Driver: # {{{
	"""
	"""

	def __init__(self,user,params):
		"""
		"""
		self.params = params
		self.params["client_id"] = user.client_id
		self.params["qualifying_time"] = ""
		self.params["race_position"]   = ""
		self.params["race_laps"]       = ""
		self.params["race_notes"]      = ""

		self._initstateless()

	def _initstateless(self):
		self._rwlock = ReadWriteLock()
	
	def getDriverAsReply(self):
		self._rwlock.acquire_read()
		try:
			ret = (
				"D",
				str(self.firstname),
				str(self.lastname),
				str(self.class_id),
				str(self.team_id),
				str(self.mod_id),
				str(self.nationality),
				str(self.helmet_colour),
				str(self.qualifying_time),
				str(self.race_position),
				str(self.race_laps),
				str(self.race_notes)
			)
		finally:
			self._rwlock.release_read()
		return ret

	def updateDriverInfos(self, params):
		"""
		"""
		self._rwlock.acquire_write()
		try:
			self.params["qualifying_time"] = params["qualifying_time"]
			self.params["race_position"]   = params["race_position"]
			self.params["race_laps"]       = params["race_laps"]
			self.params["race_notes"]      = params["race_notes"]
		finally:
			self._rwlock.release_write()

	def __getattr__(self, name):
		"""
		"""
		if self.params.has_key(name):
			return self.params[name]
		if hasattr(self,name):
			return getattr(self,name)
		raise AttributeError, "No such attribute: "+name

	def __setstate__(self,data):
		"""
		"""
		self.params = data
		self._initstateless()

	def __getstate__(self):
		"""
		"""
		return self.params
# }}}

class RaceListProtocolException(Exception): # {{{
	"""
	"""
	pass

# }}}

class RaceListRequestHandler: # {{{
	"""
	"""
	PROTOCOL_VERSION="scary v0.1"

	def __init__(self,racelist,name,paramconfig):
		"""
		"""
		self.name = name
		self._racelist = racelist
		self._keys = []
		self._checks = []
		for param in paramconfig:
			(name,type) = string.split(param,":")
			checkname = 'check_%s'%type
			if not hasattr(self,checkname):
				raise Exception("Unknown check for type=%s"%type)
			self._keys.append(name)
			self._checks.append(getattr(self,checkname))

	def handleRequest(self,client_address,values):
		"""
		"""
		if len(self._keys) != len(values):
			raise RaceListProtocolException("param amount mismatch (expecting: %s)"%self._keys)
		params = {'client_address':client_address}
		for i in range(len(self._keys)):
			value = values[i]
			key = self._keys[i]
			check = self._checks[i]
			checkresult = check(value)
			if checkresult != None:
				raise RaceListProtocolException("Error on %s: %s" % (key,checkresult))
			params[key] = value

		return self._handleRequest(client_address,params)

	def _handleRequest(self,client_address,data):
		"""
		"""
		raise NotImplementedError("RaceListRequestHandler._handleRequest is not implemented")

	def check_string(self,value):
		"""
		"""
		if len(value)>4096:
			return "string may not be longer than 4096 chars"
		return None

	def check_boolean(self,value):
		"""
		"""
		try:
			bool = string.atoi(value)
			if not 0 <= bool <= 1:
				return "value is not boolean (0 or 1)"
		except:
			return "value is not boolean (0 or 1)"
		return None

	def check_suint(self,value):
		"""
		"""
		try:
			suint = string.atoi(value)
			if not 0 <= suint <= 65535:
				return "value is no small unsigned integer"
		except:
			return "value is no small unsigned integer"
		return None

	def check_chassisbitfield(self,value):
		"""
		"""
		return self._bitfieldcheck(7,value)

	def check_carclassbitfield(self,value):
		"""
		"""
		return self._bitfieldcheck(3,value)

	def _bitfieldcheck(self,length,value):
		"""
		"""
		if len(value)!=length:
			return "lenght must be 7 chars"
		for x in value:
			if not (x=='0' or x=='1'):
				return "only 1 and 0 chars are allowed"
		return None

	def check_bandwidthfield(self,value):
		"""
		"""
		fields = string.split(value,',')
		if len(fields)!=4:
			return "expect 4 numbers separated with a kommata"
		try:
			for field in fields:
				string.atoi(field)
		except:
			return "expect 4 numbers separated with a kommata"
		return None

	def check_ip(self,value):
		"""
		"""
		fields = string.split(value,'.')
		if len(fields)!=4:
			return "expect 4 numbers between 0 and 255 separated with a dot"
		try:
			for field in fields:
				num = string.atoi(field)
				if not 0<=num<=255:
					return "expect 4 numbers between 0 and 255 separated with a dot"
		except:
			return "expect 4 numbers between 0 and 255 separated with a dot"
		return None
# }}}

class RaceListRequestHandlerLogin(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self,racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "login", [
			"protocol_version:string",
			"client_version:string",
			"client_uniqid:string"
		])

	def _handleRequest(self,client_address,params):
		"""
		"""
		if params["protocol_version"]!=self.PROTOCOL_VERSION:
			if __debug__:
				raise RaceListProtocolException("wrong protcol version - expected '%s'"%self.PROTOCOL_VERSION)
			else:
				raise RaceListProtocolException("wrong protcol version")

		user = self._racelist.getUserByUniqId(params["client_uniqid"])
		if user is None:
			user = User(params["client_uniqid"],client_address[0])
			self._racelist.addUser(user)

		return [[self.PROTOCOL_VERSION,SERVER_VERSION,user.client_id,user.outsideip]]

# }}}

class RaceListRequestHandlerHost(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "host", [
			"client_id:string", 
			"ip:ip", 
			"joinport:suint", 
			"name:string", 
			"info1:string", 
			"info2:string", 
			"comment:string", 
			"isdedicatedserver:boolean",
			"ispassworded:boolean", 
			"isbosspassworded:boolean", 
			"isauthenticedserver:boolean",
			"allowedchassis:chassisbitfield",
			"allowedcarclasses:carclassbitfield",
			"allowsengineswapping:boolean",
			"modindent:string",
			"maxlatency:suint", 
			"bandwidth:bandwidthfield",
			"maxplayers:suint",
			"trackdir:string", 
			"racetype:suint", 
			"praclength:suint"
		])

	def _handleRequest(self,client_address,params):
		"""
		"""
		self._racelist.getUser(params["client_id"])
		race = Race(params)
		self._racelist.addRace(race)
		return [[race.server_id]]

# }}}

class RaceListRequestHandlerReqFull(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "req_full", [
			"client_id:string"
		])

	def _handleRequest(self,client_address,params):
		"""
		"""
		user = self._racelist.getUser(params["client_id"])
		user.setActive()
		return self._racelist.getRaceListAsReply()

# }}}

class RaceListRequestHandlerJoin(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "join", [
			"server_id:string", 
			"client_id:string", 
			"firstname:string", 
			"lastname:string", 
			"class_id:suint", 
			"team_id:suint", 
			"mod_id:string", 
			"nationality:suint", 
			"helmet_colour:suint"
		])

	def _handleRequest(self,client_address,params):
		"""
		"""
		user = self._racelist.getUser(params["client_id"])
		driver = Driver(user,params)
		self._racelist.driverJoinRace(params["server_id"],driver)
		return [[]]

# }}}

class RaceListRequestHandlerLeave(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "leave", [
			"server_id:string", 
			"client_id:string"
		])

	def _handleRequest(self,client_address,params):
		"""
		"""
		self._racelist.driverLeaveRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class RaceListRequestHandlerEndHost(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "endhost", [
			"server_id:string",
			"client_id:string"
		])

	def _handleRequest(self,client_address,params):
		"""
		"""
		self._racelist.removeRace(params["server_id"])
		return [[]]

# }}}

class RaceListRequestHandlerReport(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "report", [
			"server_id:string"
		])

	def _handleRequest(self,client_address,params):
		"""
		"""
		# TODO
		raise RaceListProtocolException("not yet implemented")

# }}}

class RaceListRequestHandlerCopyright(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "copyright", [])

	def _handleRequest(self,client_address,params):
		"""
		"""
		return [[copyright]]

# }}}

class RaceListRequestHandlerHelp(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelist):
		"""
		"""
		RaceListRequestHandler.__init__(self, racelist, "help", [])

	def _handleRequest(self,client_address,params):
		"""
		"""
		# TODO
		raise RaceListProtocolException("not yet implemented")

# }}}

class RaceListServer(SocketServer.ThreadingTCPServer): # {{{
	"""
	"""

	def __init__(self,racelistport=27233):
		"""
		"""
		log(Log.INFO,"init %s on port %d" % (SERVER_VERSION,racelistport))
		
		self.allow_reuse_address = 1
		SocketServer.ThreadingTCPServer.__init__(self,("",racelistport),RaceListServerRequestHandler)

		self._racelist = RaceList()
		self._racelist.start()

		self._requesthandlers = {}
		self._addRequestHandler(RaceListRequestHandlerLogin(self._racelist))
		self._addRequestHandler(RaceListRequestHandlerHost(self._racelist))
		self._addRequestHandler(RaceListRequestHandlerReqFull(self._racelist))
		self._addRequestHandler(RaceListRequestHandlerJoin(self._racelist))
		self._addRequestHandler(RaceListRequestHandlerLeave(self._racelist))
		self._addRequestHandler(RaceListRequestHandlerEndHost(self._racelist))
		self._addRequestHandler(RaceListRequestHandlerReport(self._racelist))
		self._addRequestHandler(RaceListRequestHandlerCopyright(self._racelist))
		self._addRequestHandler(RaceListRequestHandlerHelp(self._racelist))

		# special code to help development
		if __debug__:
			# add some dummy races
			user = User("anuniqid","127.0.0.1")
			self._racelist.addUser(user)
			log(Log.DEBUG, 
				self.handleRequest(
					('127.0.0.1',1024),
					string.join([
						"host",
						user.client_id, 
						"80.128.87.34", 
						"32766", 
						"name", 
						"info1", 
						"info2", 
						"comment", 
						"1",
						"0", 
						"1", 
						"0",
						"1111111",
						"111",
						"0",
						"gpl67",
						"0", 
						"3,84,3,84",
						"10", 
						"solitude", 
						"1", 
						"30"
					],'\001')
				)
			)
			log(
				Log.DEBUG, self.handleRequest(
					('127.0.0.1',1024),
					string.join([
						"req_full",
						user.client_id
					],'\001')
				)
			)

	def _addRequestHandler(self,handler):
		"""
		"""
		self._requesthandlers[handler.name] = handler

	def handleRequest(self,client_address,data):
		"""
		"""
		requestdata = data.split("\001")
		if len(requestdata)==0:
			raise RaceListProtocolException("empty request")
		
		requestname = requestdata[0]
		if __debug__:
			log(Log.DEBUG,"request: "+requestdata.__str__())

		if not self._requesthandlers.has_key(requestname):
			raise RaceListProtocolException("unknown command")
		return self._requesthandlers[requestname].handleRequest(client_address,requestdata[1:])

# }}}

class RaceListServerRequestHandler(SocketServer.StreamRequestHandler): # {{{
	"""
	"""

	CLIENTINDENT="w196"
	MODE_COMPRESS="c"
	MODE_CLEARTEXT="t"
	COMPRESS_MIN_LEN = 1024*1024
	MAXSIZE=1024*1024
	CELLSEPARATOR="\001"
	ROWSEPARATOR="\002"

	def handle(self):
		"""
		"""
		log(Log.INFO, "connection from %s:%d" % self.client_address )

		try:
			data = self.readMessage()
			result = self.server.handleRequest(self.client_address,data)
			self.sendResult("ok",result)
		except RaceListProtocolException, e:
			log(Log.ERROR,e)
			self.sendError(e)
		except Exception, e:
			self.sendError(RaceListProtocolException("internal server error"))
			raise

	def readMessage(self):
		"""
		"""
		clientident = self.rfile.read(4)
		if clientident!=self.CLIENTINDENT:
			raise RaceListProtocolException("unknown client ident")

		mode = struct.unpack(">c", self.rfile.read(1))[0]
		if mode!=self.MODE_CLEARTEXT and mode!=self.MODE_COMPRESS:
			raise RaceListProtocolException("unhandled mode %s" % (mode))
		
		datasize = struct.unpack(">L", self.rfile.read(4))[0]

		if datasize>self.MAXSIZE:
			raise RaceListProtocolException("unreasonable large size=%d" %(mode))

		data = self.rfile.read(datasize)
		if len(data)!=datasize:
			raise RaceListProtocolException("client canceled connection before expected amount of data could be read")
		if mode=="c":
			data = zlib.decompress(data)

		return data

	def writeMessage(self,data):
		"""
		"""
		mode = self.MODE_CLEARTEXT
		if len(data)>self.COMPRESS_MIN_LEN:
			mode = self.MODE_COMPRESS

		if mode==self.MODE_COMPRESS:
			data = zlib.compress(data,3)

		self.wfile.write(struct.pack(">4scL", self.CLIENTINDENT, mode, len(data))+data)

	def sendError(self,exception):
		self.sendResult("err",((exception.__str__(),),))

	def sendResult(self,status,reply):
		result = status
		for list in reply:
			result += "%s%s" % (self.ROWSEPARATOR,string.join(list,self.CELLSEPARATOR))
		self.writeMessage(result)


# }}}

class Nidhoeggr: # {{{
	"""
	TODO
	- interface for Tom's secur to report racedata
	- support for the old way of reporting current race stats - like it was
	  done with vroc
	- interface to BigBrother
	- webinterface to display current stuff
	- prepare the checks to the params
	"""
	def __init__(self):
		"""
		"""
		print copyright
		self.racelistserver = RaceListServer()

	def serve_forever(self):
		"""
		"""
		try:
			log(Log.INFO,"starting racelist server")
			self.racelistserver.serve_forever()
		except KeyboardInterrupt:
			log(Log.INFO,"shutting down server");


# }}}

if __name__=="__main__":
	server = Nidhoeggr()
	server.serve_forever()

# vim:fdm=marker
