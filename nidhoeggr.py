# TODO
# - interface for Tom's secur to report racedata
# - interface to BigBrother
# - way to handle permanent servers
# - allow servers to have names instead of ips so dyndns entries can be used

SERVER_VERSION="nidhoeggr $Id: nidhoeggr.py,v 1.33.2.3 2004/03/08 20:20:20 ridcully Exp $"

DEFAULT_RACELISTPORT=30197
DEFAULT_BROADCASTPORT=30199

copyright = """
Copyright 2003,2004 Christoph Frick <rid@zefix.tv>
Copyright 2003,2004 iGOR Development Group
All Rights Reserved
This software is the proprietary information of the iGOR Development Group
Use is subject to license terms
"""

import sys
import sha
import zlib
import struct
import SocketServer
import string
import cPickle
import select
import time
import socket
import random

import tools
from tools import Log, log
import request
import paramchecks

class RaceList(tools.StopableThread): # {{{
	"""
	"""

	CLEANINTERVAL = 60.0 # seconds

	STATE_START = 1
	STATE_RUN = 2
	STATE_STOP = 3

	def __init__(self):
		"""
		"""
		tools.StopableThread.__init__(self,self.CLEANINTERVAL)

		self._users = {}
		self._usersuniqids = {}
		self._races = {}
		self._racesbroadcasts = {}
		self._reqfull = []

		self._state = RaceList.STATE_START

		self._users_rwlock = tools.ReadWriteLock()
		self._races_rwlock = tools.ReadWriteLock()

		self._load()

	def hasUser(self, client_id):
		"""
		"""
		return self._users.has_key(client_id)

	def hasRace(self, server_id):
		"""
		"""
		return self._races.has_key(server_id)

	def addUser(self,user):
		"""
		"""
		self._users_rwlock.acquire_write()
		try:
			client_id = user.params['client_id']
			if not self.hasUser(client_id):
				self._users[client_id] = user
				self._usersuniqids[user.params['client_uniqid']] = user
			else:
				raise RaceListProtocolException(400, "user already registered")
		finally:
			self._users_rwlock.release_write()

	def removeUser(self,client_id):
		"""
		"""
		self._users_rwlock.acquire_write()
		try:
			if self.hasUser(client_id):
				if self._usersuniqids.has_key(self._users[client_id].params['client_uniqid']):
					del self._usersuniqids[self._users[client_id].params['client_uniqid']]
				del self._users[client_id]
		finally:
			self._users_rwlock.release_write()

	def getUser(self,client_id):
		"""
		"""
		self._users_rwlock.acquire_read()
		try:
			if not self.hasUser(client_id):
				raise RaceListProtocolException(401, "user unknown/not logged in")
			ret = self._users[client_id]
			ret.setActive()
		finally:
			self._users_rwlock.release_read()
		return ret

	def getUserByUniqId(self,client_uniqid):
		"""
		"""
		if self._usersuniqids.has_key(client_uniqid):
			return self._usersuniqids[client_uniqid]
		return None

	def addRace(self,race):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			if not self.hasRace(race.params['server_id']):
				self._races[race.params['server_id']] = race
				self._racesbroadcasts[race.params['broadcastid']] = race
			else:
				raise RaceListProtocolException(400, "race already registered")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()

	def removeRace(self,server_id,client_id):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			if self.hasRace(server_id):
				if self._races[server_id].params['client_id']!=client_id:
					raise RaceListProtocolException(401, "authorization required")
				broadcastid = self._races[server_id].params['broadcastid']
				if self._racesbroadcasts.has_key(broadcastid):
					del self._racesbroadcasts[broadcastid]
				del self._races[server_id]
			else:
				raise RaceListProtocolException(404, "unknown server_id")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()
	
	def driverJoinRace(self,server_id,driver):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			for race in self._races.values():
				race.removeDriver(driver.params['client_id'])
			if self.hasRace(server_id):
				self._races[server_id].addDriver(driver)
			else:
				raise RaceListProtocolException(404, "unknown server_id")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()
	
	def driverLeaveRace(self,server_id,client_id):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			for race in self._races.values():
				race.removeDriver(client_id)
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

	def updateRaceViaBroadcast(self, broadcastid, players, maxplayers, racetype, trackdir, sessiontype, sessionleft):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			if self._racesbroadcasts.has_key(broadcastid):
				self._racesbroadcasts[broadcastid].updateRaceViaBroadcast(players, maxplayers, racetype, trackdir, sessiontype, sessionleft)
				self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()

	def _run(self):
		"""
		lurks behind the scenes and cleans the._races and the._users
		"""
		if self._state <> RaceList.STATE_RUN: 
			return
		currenttime = time.time()
		usercount = 0
		userdelcount = 0
		racecount = 0
		racedelcount = 0
		for client_id in self._users.keys():
			usercount = usercount + 1
			if self._users[client_id].checkTimeout(currenttime):
				if __debug__:
					log(Log.DEBUG, "removing user %s" % client_id )
				userdelcount = userdelcount + 1
				self.removeUser(client_id)

		for server_id in self._races.keys():
			racecount = racecount + 1
			if self._races[server_id].checkTimeout(currenttime):
				if __debug__:
					log(Log.DEBUG, "removing race %s" % server_id )
				racedelcount = racedelcount + 1
				self.removeRace(server_id, self._races[server_id].params['client_id'])

		log(log.INFO, "cleanup: %d/%d users; %d/%d races" % (userdelcount,usercount,racedelcount,racecount))

	def _join(self):
		"""
		stores the current racelist in the given file
		"""
		filename='racelist.cpickle'
		log(Log.INFO, "store racelist to file '%s'" % filename )
		self._state = RaceList.STATE_STOP
		self._users_rwlock.acquire_write()
		self._races_rwlock.acquire_write()
		try:
			outf = open(filename, "w")
			cPickle.dump(self._users, outf, 1 )
			cPickle.dump(self._races, outf, 1 )
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
			self._users_rwlock.acquire_write()
			self._races_rwlock.acquire_write()
			try:
				self._users = cPickle.load(inf)
				self._races = cPickle.load(inf)
			finally:
				self._users_rwlock.release_write()
				self._races_rwlock.release_write()
			self._usersuniqids = {}
			for user in self._users.values():
				self._usersuniqids[user.params['client_uniqid']] = user
			inf.close()
		except Exception,e:
			log(Log.WARNING, "failed to load racelist state from file '%s': %s" % (filename, e) )
		self._buildRaceListAsReply()
		self._state = RaceList.STATE_RUN

# }}}

class Race(tools.IdleWatcher): # {{{
	"""
	"""
	
	def __init__(self,params):
		"""
		"""
		self.params = params
		if self.params['ip']=='127.0.0.1':
			self.params['ip'] = random.choice([ '193.99.144.71', '206.231.101.19', '80.15.238.104', '80.15.238.102' ])
		self.params["server_id"] = sha.new("%s%s%s%s%s" % (self.params['client_id'], self.params['ip'], self.params['joinport'], time.time(), random.randint(0,1000000))).hexdigest()
		self.params["broadcastid"] = "%s:%s" % (self.params['ip'], self.params['joinport'])

		self.params["sessiontype"] = 0
		self.params["sessionleft"] = self.params['praclength']
		self.params["players"]     = 0
		
		self.drivers = {}

		self._initstateless()

	def _initstateless(self):
		"""
		"""
		tools.IdleWatcher.__init__(self,300.0)
		self._rwlock = tools.ReadWriteLock()

	def hasDriver(self, client_id):
		"""
		"""
		return self.drivers.has_key(client_id)

	def addDriver(self,driver):
		"""
		"""
		client_id = driver.params['client_id']
		if not self.hasDriver(client_id):
			self.setActive()
			self.drivers[client_id] = driver
		# silently ignore the request, if this driver has already joined the race

	def removeDriver(self,client_id):
		"""
		"""
		if self.hasDriver(client_id):
			self.setActive()
			del self.drivers[client_id]
		# silently ignore the request, if there is no driver with this id in the race
			
	def updateRaceViaBroadcast(self, players, maxplayers, racetype, trackdir, sessiontype, sessionleft):
		"""
		"""
		self.setActive()
		self.params['players']     = players
		self.params['maxplayers']  = maxplayers
		self.params['racetype']    = racetype
		self.params['trackdir']    = trackdir
		self.params['sessiontype'] = sessiontype
		self.params['sessionleft'] = sessionleft

	def getRaceAsReply(self):
		"""
		"""
		ret = (
			"R",
			str(self.params['server_id']),
			str(self.params['ip']),
			str(self.params['joinport']),
			str(self.params['name']),
			str(self.params['info1']),
			str(self.params['info2']),
			str(self.params['comment']),
			str(self.params['isdedicatedserver']),
			str(self.params['ispassworded']),
			str(self.params['isbosspassworded']),
			str(self.params['isauthenticedserver']),
			str(self.params['allowedchassis']),
			str(self.params['allowedcarclasses']),
			str(self.params['allowsengineswapping']),
			str(self.params['modindent']),
			str(self.params['maxlatency']),
			str(self.params['bandwidth']),
			str(self.params['players']),
			str(self.params['maxplayers']),
			str(self.params['trackdir']),
			str(self.params['racetype']),
			str(self.params['praclength']),
			str(self.params['sessiontype']),
			str(self.params['sessionleft']),
			str(self.params['aiplayers']),
			str(self.params['numraces']),
			str(self.params['repeatcount']),
			str(self.params['flags'])
		)
		return ret

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

class User(tools.IdleWatcher): # {{{
	"""
	"""

	def __init__(self,client_uniqid,outsideip):
		"""
		"""
		self.params = {}
		tools.IdleWatcher.__init__(self, 3600.0)
		self.params['client_uniqid'] = client_uniqid
		self.params['outsideip'] = outsideip
		self.params['client_id'] = sha.new("%s%s%s" % (client_uniqid, time.time(), random.randint(0,1000000))).hexdigest()

# }}}

class Driver: # {{{
	"""
	"""

	def __init__(self,user,params):
		"""
		"""
		self.params = params
		self.params["client_id"] = user.params['client_id']
		self.params["qualifying_time"] = ""
		self.params["race_position"]   = ""
		self.params["race_laps"]       = ""
		self.params["race_notes"]      = ""

		self._initstateless()

	def _initstateless(self):pass
	
	def getDriverAsReply(self):
		ret = (
			"D",
			str(self.params['firstname']),
			str(self.params['lastname']),
			str(self.params['class_id']),
			str(self.params['team_id']),
			str(self.params['mod_id']),
			str(self.params['nationality']),
			str(self.params['helmet_colour']),
			str(self.params['qualifying_time']),
			str(self.params['race_position']),
			str(self.params['race_laps']),
			str(self.params['race_notes'])
		)
		return ret

	def updateDriverInfos(self, params):
		"""
		"""
		self.params["qualifying_time"] = params["qualifying_time"]
		self.params["race_position"]   = params["race_position"]
		self.params["race_laps"]       = params["race_laps"]
		self.params["race_notes"]      = params["race_notes"]

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
	def __init__(self,id,description):
		Exception.__init__(self, description)
		self.id = id
		self.description = description

# }}}

class Server(SocketServer.ThreadingTCPServer): # {{{
	"""
	"""

	def __init__(self,servername,racelistport=DEFAULT_RACELISTPORT,broadcastport=DEFAULT_BROADCASTPORT):
		"""
		"""
		self._servername = servername
		
		print copyright
		log(Log.INFO,"init %s on %s:%d" % (SERVER_VERSION,servername,racelistport))

		self.allow_reuse_address = 1
		SocketServer.ThreadingTCPServer.__init__(self,("",racelistport),ServerRequestHandler)

		self._racelist = RaceList()

		self._broadcastserver = BroadCastServer(self._racelist,broadcastport)

		self._requesthandlers = {}
		self._addRequestHandler(request.RequestHandlerLogin(self))
		self._addRequestHandler(request.RequestHandlerReqFull(self))
		self._addRequestHandler(request.RequestHandlerHost(self))
		self._addRequestHandler(request.RequestHandlerJoin(self))
		self._addRequestHandler(request.RequestHandlerLeave(self))
		self._addRequestHandler(request.RequestHandlerEndHost(self))
		self._addRequestHandler(request.RequestHandlerReport(self))
		self._addRequestHandler(request.RequestHandlerCopyright(self))
		self._addRequestHandler(request.RequestHandlerHelp(self))

		self.inshutdown = 0

	def _addRequestHandler(self,handler):
		"""
		"""
		self._requesthandlers[handler.command] = handler

	def handleRequest(self,client_address,request):
		"""
		"""
		if len(request)==0 or len(request[0])==0:
			raise RaceListProtocolException(400, "empty request")
		
		command = request[0][0]
		if __debug__:
			log(Log.DEBUG,"request: "+str(request))

		if not self._requesthandlers.has_key(command):
			raise RaceListProtocolException(400, "unknown command")
		log(log.INFO, "command ``%s'' from %s:%d" % (command, client_address[0], client_address[1]))
		return self._requesthandlers[command].handleRequest(client_address,request[0][1:])

	def start(self):
		"""
		"""
		self._racelist.start()
		self._broadcastserver.start()
		self.serve_forever()

	def stop(self):
		"""
		"""
		log(Log.INFO,"shutting down server");
		self.inshutdown = 1
		log(Log.INFO,"waiting for broadcast server");
		self._broadcastserver.join()
		log(Log.INFO,"waiting for racelist");
		self._racelist.join()

	def inShutdown(self):
		return self.inshutdown!=0

# }}}

class Middleware: # {{{
	"""
	"""

	CLIENTINDENT="w196"
	MODE_COMPRESS="c"
	MODE_CLEARTEXT="t"
	COMPRESS_MIN_LEN = 1024
	COMPRESSIONLEVEL = 3
	MAXSIZE=1024*1024
	CELLSEPARATOR="\001"
	ROWSEPARATOR="\002"

	def readData(self):
		"""
		"""
		clientident = self.rfile.read(4)
		if clientident!=self.CLIENTINDENT:
			raise RaceListProtocolException(400, "unknown client ident")

		try:
			rawmode = self.rfile.read(1)
		except error,e:
			log(Log.ERROR,e)
			raise RaceListProtocolException(400, "error reading mode")
		if not rawmode:
			raise RaceListProtocolException(400, "error reading mode")

		mode = struct.unpack(">c", rawmode)[0]

		if mode!=self.MODE_CLEARTEXT and mode!=self.MODE_COMPRESS:
			raise RaceListProtocolException(400, "unhandled mode %s" % (mode))
		
		try:
			rawdatasize = self.rfile.read(4)
		except error,e:
			log(Log.ERROR,e)
			raise RaceListProtocolException(400, "error reading datasize")
		if len(rawdatasize)!=4:
			raise RaceListProtocolException(400, "error reading datasize")

		datasize = struct.unpack(">L", rawdatasize)[0]

		if datasize>self.MAXSIZE:
			raise RaceListProtocolException(400, "unreasonable large size=%d" %(datasize))

		if mode==self.MODE_COMPRESS:
			try:
				rawuncompresseddatasize = self.rfile.read(4)
			except error,e:
				log(Log.ERROR,e)
				raise RaceListProtocolException(400, "error reading uncompressed datasize")
			if len(rawuncompresseddatasize)!=4:
				raise RaceListProtocolException(400, "error reading uncompressed datasize")

			uncompresseddatasize = struct.unpack(">L", rawuncompresseddatasize)[0]

			if uncompresseddatasize>self.MAXSIZE:
				raise RaceListProtocolException(400, "unreasonable large uncompressed size=%d" %(uncompresseddatasize))

		try:
			data = self.rfile.read(datasize)
		except socket.error, e:
			log(Log.ERROR,e)
			raise RaceListProtocolException(400, "error reading data")

		if len(data)!=datasize:
			raise RaceListProtocolException(400, "error reading data")

		if mode=="c":
			try:
				data = zlib.decompress(data)
			except zlib.error,e:
				log(Log.ERROR,e)
				raise RaceListProtocolException(400, "error decompressing  data")

		return data

	def sendData(self,data):
		"""
		"""
		mode = self.MODE_CLEARTEXT
		l = len(data)
		if l>self.COMPRESS_MIN_LEN:
			mode = self.MODE_COMPRESS

		if mode==self.MODE_COMPRESS:
			data = zlib.compress(data,self.COMPRESSIONLEVEL)
			if __debug__:
				log(Log.DEBUG, "compression: %d -> %d" % (l,len(data)))
			self.wfile.write(struct.pack(">4scLL", self.CLIENTINDENT, mode, len(data), l)+data)
		else:
			self.wfile.write(struct.pack(">4scL", self.CLIENTINDENT, mode, len(data))+data)

	def send(self,reply,exception=None):
		"""
		"""
		result = []
		if exception is not None:
			result.append("%d%s%s" % (exception.id,self.CELLSEPARATOR,exception.description))
		for list in reply:
			result.append(string.join(list,self.CELLSEPARATOR))
		self.sendData(string.join(result,self.ROWSEPARATOR))

	def read(self):
		"""
		"""
		data = self.readData()
		request = []
		for row in data.split(self.ROWSEPARATOR):
			request.append(row.split(self.CELLSEPARATOR))
		return request

# }}}

class ServerRequestHandler(SocketServer.StreamRequestHandler, Middleware): # {{{
	"""
	"""

	OK = RaceListProtocolException(200,'OK')

	def handle(self):
		"""
		"""
		log(Log.DEBUG, "connection from %s:%d" % self.client_address )

		try:
			request = self.read()
			result = self.server.handleRequest(self.client_address,request)
			self.send(result, self.OK)
		except RaceListProtocolException, e:
			# racelist errors are logged and sent to the client
			log(Log.ERROR,e)
			self.send([], e)
		except IOError, e:
			# something went tits up with the connection - we cant
			# help here just log and bailout
			log(Log.ERROR, e)
		except Exception, e:
			# this are errors that should not be - try to send an
			# error to the client, that something went wrong and
			# re-raise the exception again
			self.send([], RaceListProtocolException(500, "internal server error"))
			raise

# }}}

class BroadCastServer(SocketServer.ThreadingUDPServer, tools.StopableThread): # {{{
	"""
	"""

	def __init__(self,racelist,broadcastport=DEFAULT_BROADCASTPORT):
		"""
		"""
		log(Log.INFO,"init broadcast listen server on port %d" % (broadcastport))

		tools.StopableThread.__init__(self)
		
		self.racelist = racelist
		self.allow_reuse_address = 1
		SocketServer.ThreadingUDPServer.__init__(self,("",broadcastport),BroadCastServerRequestHandler)

	def _run(self):
		"""
		"""
		(infd,outfd,errfd) = select.select([self.socket], [], [], 1.0) # timout 1s
		if self.socket in infd:
			self.handle_request()
# }}}

class BroadCastServerRequestHandler(SocketServer.DatagramRequestHandler): # {{{
	"""
	"""
	def handle(self):
		"""
		"""
		try:
			line = self.rfile.read(4096)
			version, joinport, servername, trackdir, cardir, xplayers, classes, racetype, junk, hassession, sessiontype, timeinsession, passworded, maxping = line.split("\001")
			broadcastid = "%s:%s" % (self.client_address[0],joinport)
			players,maxplayers = xplayers.split('/')
			if hassession=='N':
				sessiontype = 0
				sessionleft = 0
			else:
				sessionleft = timeinsession[1:]

			error = paramchecks.check_players(players)
			if error is not None:
				raise Exception('in broadcast players check failed: %s' % error)
			error = paramchecks.check_players(maxplayers)
			if error is not None:
				raise Exception('in broadcast maxplayers check failed: %s' % error)
			error = paramchecks.check_racetype(racetype)
			if error is not None:
				raise Exception('in broadcast racetype check failed: %s' % error)
			error = paramchecks.check_string(trackdir)
			if error is not None:
				raise Exception('in broadcast trackdir check failed: %s' % error)
			error = paramchecks.check_sessiontype(sessiontype)
			if error is not None:
				raise Exception('in broadcast sessiontype check failed: %s' % error)
			error = paramchecks.check_suint(sessionleft)
			if error is not None:
				raise Exception('in broadcast sessionleft check failed: %s' % error)

			if __debug__:
				log(Log.DEBUG, "got ping info: broadcastid=%s players=%s maxplayers=%s racetype=%s trackdir=%s sessiontype=%s sessionleft=%s" % (broadcastid, players, maxplayers, racetype, trackdir, sessiontype, sessionleft))
			self.server.racelist.updateRaceViaBroadcast(broadcastid, players, maxplayers, racetype, trackdir, sessiontype, sessionleft)
		except Exception, e:
			# can not much do about it
			log(Log.DEBUG, e)

# }}}

class Client: # {{{
	"""
	"""

	def __init__(self, client_uniq_id, server, port=DEFAULT_RACELISTPORT):
		"""
		"""
		self.server_address = (server,port)
		
		loginrequest = RequestSender(self, [['login', request.PROTOCOL_VERSION, SERVER_VERSION, client_uniq_id]])
		self.client_id = loginrequest.result[0][2]

# }}}

class RequestSender(Middleware): # {{{
	"""
	"""

	def __init__(self, client, params):
		"""
		"""
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(client.server_address)
		self.rfile = s.makefile('rb')
		self.wfile = s.makefile('wb')
		self.send(params)
		self.wfile.close()
		result = self.read()
		self.rfile.close()
		s.close()
		self.status = RaceListProtocolException(int(result[0][0]), result[0][1])
		if self.status.id <> 200:
			raise self.status
		self.result = result[1:]

# }}}

# vim:fdm=marker
