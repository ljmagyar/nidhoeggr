# TODO
# - interface for Tom's secur to report racedata
# - interface to BigBrother
# - way to handle permanent servers
# - allow servers to have names instead of ips so dyndns entries can be used

SERVER_VERSION="nidhoeggr $Id: nidhoeggr.py,v 1.47 2004/03/25 20:19:58 ridcully Exp $"

__copyright__ = """
(c) Copyright 2003-2004 Christoph Frick <rid@zefix.tv>
(c) Copyright 2003-2004 iGOR Development Group
All Rights Reserved
This software is the proprietary information of the iGOR Development Group
Use is subject to license terms
"""
print __copyright__

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

from config import config, DEFAULT_RACELISTPORT, DEFAULT_BROADCASTPORT
from tools import *
import request
import paramchecks

class RaceList(StopableThread): # {{{

	STATE_START = 1
	STATE_RUN = 2
	STATE_STOP = 3

	def __init__(self):
		StopableThread.__init__(self,config.racelist_clean_interval)

		self._users = {}
		self._usersuniqids = {}
		self._races = {}
		self._racesbroadcasts = {}
		self._reqfull = []

		self._state = RaceList.STATE_START

		self._users_rwlock = ReadWriteLock()
		self._races_rwlock = ReadWriteLock()

		self._load()

	def hasUser(self, client_id):
		return self._users.has_key(client_id)

	def hasRace(self, server_id):
		return self._races.has_key(server_id)

	def addUser(self,user):
		self._users_rwlock.acquire_write()
		try:
			client_id = user.params['client_id']
			if not self.hasUser(client_id):
				self._users[client_id] = user
				self._usersuniqids[user.params['client_uniqid']] = user
			else:
				raise Error(Error.REQUESTERROR, "user already registered")
		finally:
			self._users_rwlock.release_write()

	def removeUser(self,client_id):
		self._users_rwlock.acquire_write()
		try:
			if self.hasUser(client_id):
				if self._usersuniqids.has_key(self._users[client_id].params['client_uniqid']):
					del self._usersuniqids[self._users[client_id].params['client_uniqid']]
				del self._users[client_id]
		finally:
			self._users_rwlock.release_write()

	def getUser(self,client_id):
		self._users_rwlock.acquire_read()
		try:
			if not self.hasUser(client_id):
				raise Error(Error.AUTHERROR, "user unknown/not logged in")
			ret = self._users[client_id]
			ret.setActive()
			return ret
		finally:
			self._users_rwlock.release_read()

	def getUserByUniqId(self,client_uniqid):
		if self._usersuniqids.has_key(client_uniqid):
			return self._usersuniqids[client_uniqid]
		return None

	def addRace(self,race):
		self._races_rwlock.acquire_write()
		try:
			if not self.hasRace(race.params['server_id']):
				self._races[race.params['server_id']] = race
				self._racesbroadcasts[race.params['broadcastid']] = race
			else:
				raise Error(Error.REQUESTERROR, "race already registered")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()

	def removeRace(self,server_id,client_id):
		self._races_rwlock.acquire_write()
		try:
			if self.hasRace(server_id):
				if self._races[server_id].params['client_id']!=client_id:
					raise Error(Error.AUTHERROR, "authorization required")
				broadcastid = self._races[server_id].params['broadcastid']
				if self._racesbroadcasts.has_key(broadcastid):
					del self._racesbroadcasts[broadcastid]
				del self._races[server_id]
			else:
				raise Error(Error.NOTFOUND, "unknown server_id")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()
	
	def driverJoinRace(self,server_id,driver):
		self._races_rwlock.acquire_write()
		try:
			for race in self._races.values():
				race.removeDriver(driver.params['client_id'])
			if self.hasRace(server_id):
				self._races[server_id].addDriver(driver)
			else:
				raise Error(Error.NOTFOUND, "unknown server_id")
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()
	
	def driverLeaveRace(self,server_id,client_id):
		self._races_rwlock.acquire_write()
		try:
			for race in self._races.values():
				race.removeDriver(client_id)
			self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()

	def _buildRaceListAsReply(self):
		self.reqfull = []
		for race in self._races.values():
			self.reqfull.append(race.getRaceAsReply())
			for driver in race.drivers.values():
				self.reqfull.append(driver.getDriverAsReply())

	def getRaceListAsReply(self):
		ret = []
		self._races_rwlock.acquire_read()
		try:
			return self.reqfull
		finally:
			self._races_rwlock.release_read()

	def updateRaceViaBroadcast(self, broadcastid, players, maxplayers, racetype, trackdir, sessiontype, sessionleft):
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
		self._save()

	def _save(self):
		"""
		stores the current racelist in the given file
		"""
		filename = config.file_racelist
		log(Log.INFO, "store racelist to file '%s'" % filename )
		self._state = RaceList.STATE_STOP
		self._users_rwlock.acquire_write()
		self._races_rwlock.acquire_write()
		try:
			try:
				outf = open(filename, "w")
				cPickle.dump(self._users, outf, 1 )
				cPickle.dump(self._races, outf, 1 )
				outf.close()
			except Exception, e:
				log(Log.WARNING,"failed to save racelist state to file '%s': %s" % (filename,e) )
		finally:
			self._users_rwlock.release_write()
			self._races_rwlock.release_write()

	def _load(self):
		"""
		loads the racelist from the given file
		"""
		filename = config.file_racelist
		log(Log.INFO, "load racelist from file '%s'" % filename )
		self._users_rwlock.acquire_write()
		self._races_rwlock.acquire_write()
		try:
			try:
				inf = open(filename, "r")
				self._users = cPickle.load(inf)
				self._races = cPickle.load(inf)
				self._usersuniqids = {}
				for user in self._users.values():
					self._usersuniqids[user.params['client_uniqid']] = user
				inf.close()
			except Exception,e:
				log(Log.WARNING, "failed to load racelist state from file '%s': %s" % (filename, e) )
		finally:
			self._users_rwlock.release_write()
			self._races_rwlock.release_write()
		self._buildRaceListAsReply()
		self._state = RaceList.STATE_RUN

# }}}

class Race(IdleWatcher): # {{{
	
	
	def __init__(self,params):
		self.params = params
		if __debug__:
			if self.params['ip']=='127.0.0.1':
				self.params['ip'] = random.choice([ '193.99.144.71', '206.231.101.19', '80.15.238.104', '80.15.238.102' ])
		self.params["server_id"] = sha.new("%s%s%s%s%s" % (self.params['client_id'], self.params['ip'], self.params['joinport'], time.time(), random.randint(0,1000000))).hexdigest()
		self.params["broadcastid"] = "%s:%s" % (self.params['ip'], self.params['joinport'])

		self.params["sessiontype"] = 0
		self.params["sessionleft"] = self.params['praclength']
		self.params["players"]     = 0
		
		self.drivers = {}

		IdleWatcher.__init__(self,config.race_timeout)

		self._initstateless()

	def _initstateless(self):
		self._rwlock = ReadWriteLock()

	def hasDriver(self, client_id):
		return self.drivers.has_key(client_id)

	def addDriver(self,driver):
		client_id = driver.params['client_id']
		if not self.hasDriver(client_id):
			self.setActive()
			self.drivers[client_id] = driver
		# silently ignore the request, if this driver has already joined the race

	def removeDriver(self,client_id):
		if self.hasDriver(client_id):
			self.setActive()
			del self.drivers[client_id]
		# silently ignore the request, if there is no driver with this id in the race
			
	def updateRaceViaBroadcast(self, players, maxplayers, racetype, trackdir, sessiontype, sessionleft):
		self.setActive()
		self.params['players']     = players
		self.params['maxplayers']  = maxplayers
		self.params['racetype']    = racetype
		self.params['trackdir']    = trackdir
		self.params['sessiontype'] = sessiontype
		self.params['sessionleft'] = sessionleft

	def getRaceAsReply(self):
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
		return (self.params,self.drivers)
	
	def __setstate__(self,data):
		(self.params, self.drivers) = data
		self._initstateless()
			
# }}}

class User(IdleWatcher): # {{{
	

	def __init__(self,client_uniqid,outside_ip):
		self.params = {}
		IdleWatcher.__init__(self, config.user_timeout)
		self.params['client_uniqid'] = client_uniqid
		self.params['outside_ip'] = outside_ip
		self.params['client_id'] = sha.new("%s%s%s" % (client_uniqid, time.time(), random.randint(0,1000000))).hexdigest()

# }}}

class RLServer(IdleWatcher): # {{{
	def __init__(self,params):
		self.params = params
		IdleWatcher.__init__(self, config.server_timeout)
		self._initstateless()

	def _initstateless(self):
		self.requests = []
		self.setActive()
	
	def getUpdate(self):
		self.setActive()
		update = self.requests
		self.requests = []
		return update

	def addRequest(self, values):
		self.requests.append(values)

	def __getstate__(self):
		return self.params

	def __setstate__(self, data):
		self.params = data
		self._initstateless()
# }}}

class RLServerList(StopableThread): # {{{

	def __init__(self):
		StopableThread.__init__(self,config.serverlist_clean_interval)
		self._rls_id = sha.new("%s%s%s" % (SERVER_VERSION,config.servername,config.racelistport)).hexdigest()
		self._servers = {}
		self._servers_rwlock = ReadWriteLock()
		self._load()

	def hasRLServer(self, rls_id):
		return self._servers.has_key(rls_id)

	def getRLServer(self, rls_id):
		self._servers_rwlock.acquire_read()
		try:
			if not self.hasRLServer(rls_id):
				raise Error(Error.AUTHERROR, "race list server unknown/not logged in")
			return self._servers[rls_id]
		finally:
			self._servers_rwlock.release_read()

	def addRLServer(self,rls):
		rls_id = server.params['rls_id']
		self._servers_rwlock.acquire_write()
		try:
			if not self.hasRLServer(rls_id):
				self._servers[rls_id] = rls
		finally:
			self._servers_rwlock.release_write()
		self._buildServerListReply()

	def delRLServer(self,rls_id,ip):
		rls_id = params['rls_id']
		# check for unknown server
		if not self._servers.has_key(rls_id):
			return
		# check for the same ip, as the server has registered
		rls = self._servers[rls_id]
		if not ip==rls.params['ip']:
			return
		# delete the server from the list
		self._servers_rwlock.acquire_write()
		try:
			del self._servers[rls_id]
		finally:
			self._servers_rwlock.release_write()
		self._buildServerListReply()

	def getUpdate(self, rls_id):
		self._servers_rwlock.acquire_write()
		try:
			if self._servers.has_key(rls_id):
				return self._servers[rls_id].getUpdate()
			return None
		finally:
			self._servers_rwlock.release_write()

	def addRequest(self, values):
		self._servers_rwlock.acquire_write()
		try:
			for server in self._servers.values():
				server.addRequest(values)
		finally:
			self._servers_rwlock.release_write()

	def _load(self):
		filename = config.file_serverlist
		log(Log.INFO, "load the server list from file '%s'" % (filename))
		try:
			f = open(filename, "r")
			self._servers = cPickle.load(f)
			f.close()
		except Exception, e:
			log(Log.WARNING, "failed to load server list from file '%s': %s" % (filename, e))
		self._buildServerListReply()
		self.client = None
	
	def _save(self):
		filename = config.file_serverlist
		log(Log.INFO, "save the server list to file '%s'" % (filename))
		try:
			f = open(filename, "w")
			try:
				self._servers_rwlock.acquire_read()
				cPickle.dump(self._servers,f,1)
			finally:
				self._servers_rwlock.release_read()
			f.close()
		except Exception, e:
			log(Log.WARNING, "failed to save server list to file '%s': %s" % (filename, e))

	def _buildServerListReply(self):
		self._servers_rwlock.acquire_read()
		try:
			self._simpleserverlistreply = []
			self._fullserverlistreply = []
			for server in self._servers.values():
				self._simpleserverlistreply.append((server.params['rls_id'], server.params['ip'], server.params['port']))
				self._fullserverlistreply.append((server.params['rls_id'], server.params['ip'], server.params['port'], server.params['maxload']))
		finally:
			self._servers_rwlock.release_read()

	def getSimpleServerListAsReply(self):
		return self._simpleserverlistreply

	def getFullServerListAsReply(self):
		return self._fullserverlistreply

	def _join(self):
		self._save()

	def _run(self):
		if self.client is None:
			self.register()
		ct = time.time()
		self._servers_rwlock.acquire_write()
		try:
			for rls_id in self._servers.keys():
				server = self._servers[rls_id]
				if server.checkTimeout(ct):
					log.Log(Log.INFO, "dropping race list server %s (%s:%d) due to a a time out" % (server.params['rls_id'], server.params['name'], server.params['port']))
					del self._servers[rls_id]
		finally:
			self._servers_rwlock.release_write()

	def getInitServer(self):
		if len(self._servers):
			rls = self._servers.values()[0]
			return (rls.params['name'],rls.params['port'])
		return (config.initserver_name,config.initserver_port)

	def register(self):
		initserver_name,initserver_port = self.getInitServer()
		try:
			client = Client(initserver_name,initserver_port)
			result = client.doRequest([["rls_register", self._rls_id, config.servername, str(config.racelistport), str(config.server_maxload)]])
			for row in result:
				self._serverlist.addRLServer(row)
		except Exception, e:
			log(Log.WARNING, "Error on registering to init server: %s" % e)
	
# }}}

class Driver: # {{{
	

	def __init__(self,user,params):
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
		self.params["qualifying_time"] = params["qualifying_time"]
		self.params["race_position"]   = params["race_position"]
		self.params["race_laps"]       = params["race_laps"]
		self.params["race_notes"]      = params["race_notes"]

	def __setstate__(self,data):
		self.params = data
		self._initstateless()

	def __getstate__(self):
		return self.params
# }}}

class Error(Exception): # {{{

	OK = 200
	REQUESTERROR = 400
	AUTHERROR = 401
	NOTFOUND = 404
	INTERNALERROR = 500
	UNIMPLMENTED = 501

	def __init__(self,id,description):
		Exception.__init__(self, description)
		self.id = id
		self.description = description

# }}}

class Middleware: # {{{
	

	CLIENTINDENT="w196"
	MODE_COMPRESS="c"
	MODE_CLEARTEXT="t"
	COMPRESS_MIN_LEN = 1024
	COMPRESSIONLEVEL = 3
	MAXSIZE=1024*1024
	CELLSEPARATOR="\001"
	ROWSEPARATOR="\002"

	def readData(self):
		clientident = self.rfile.read(4)
		if clientident!=self.CLIENTINDENT:
			raise Error(Error.REQUESTERROR, "unknown client ident")

		try:
			rawmode = self.rfile.read(1)
		except socket.error,e:
			log(Log.ERROR,e)
			raise Error(Error.REQUESTERROR, "error reading mode")
		if not rawmode:
			raise Error(Error.REQUESTERROR, "error reading mode")

		mode = struct.unpack(">c", rawmode)[0]

		if mode!=self.MODE_CLEARTEXT and mode!=self.MODE_COMPRESS:
			raise Error(Error.REQUESTERROR, "unhandled mode '%s'" % (mode))
		
		try:
			rawdatasize = self.rfile.read(4)
		except socket.error,e:
			log(Log.ERROR,e)
			raise Error(Error.REQUESTERROR, "error reading datasize")
		if len(rawdatasize)!=4:
			raise Error(Error.REQUESTERROR, "error reading datasize")

		datasize = struct.unpack(">L", rawdatasize)[0]

		if datasize>self.MAXSIZE:
			raise Error(Error.REQUESTERROR, "unreasonable large size=%d" %(datasize))

		if mode==self.MODE_COMPRESS:
			try:
				rawuncompresseddatasize = self.rfile.read(4)
			except socket.error,e:
				log(Log.ERROR,e)
				raise Error(Error.REQUESTERROR, "error reading uncompressed datasize")
			if len(rawuncompresseddatasize)!=4:
				raise Error(Error.REQUESTERROR, "error reading uncompressed datasize")

			uncompresseddatasize = struct.unpack(">L", rawuncompresseddatasize)[0]

			if uncompresseddatasize>self.MAXSIZE:
				raise Error(Error.REQUESTERROR, "unreasonable large uncompressed size=%d" %(uncompresseddatasize))

		try:
			data = self.rfile.read(datasize)
		except socket.error, e:
			log(Log.ERROR,e)
			raise Error(Error.REQUESTERROR, "error reading data")

		if len(data)!=datasize:
			raise Error(Error.REQUESTERROR, "error reading data")

		if mode=="c":
			try:
				data = zlib.decompress(data)
			except zlib.error,e:
				log(Log.ERROR,e)
				raise Error(Error.REQUESTERROR, "error decompressing  data")

		return data

	def sendData(self,data):
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

	def send(self,data):
		retdata = []
		for row in data:
			retdata.append(string.join(row,self.CELLSEPARATOR))
		self.sendData(string.join(retdata,self.ROWSEPARATOR))

	def reply(self,exception,data=[]):
		self.send([[str(exception.id),exception.description]]+data)

	def read(self):
		data = self.readData()
		request = []
		for row in data.split(self.ROWSEPARATOR):
			request.append(row.split(self.CELLSEPARATOR))
		return request

# }}}

class RaceListServer(SocketServer.ThreadingTCPServer, StopableThread): # {{{

	def __init__(self, racelist, serverlist):
		log(Log.INFO,"init racelist server on %s:%d" % (config.servername,config.racelistport))
		StopableThread.__init__(self)

		self.allow_reuse_address = 1
		SocketServer.ThreadingTCPServer.__init__(self,("",config.racelistport),RaceListServerRequestHandler)

		self._racelist = racelist
		self._serverlist = serverlist

		self._requesthandlers = {}
		self._addRequestHandler(request.HandlerLogin(self))
		self._addRequestHandler(request.HandlerReqFull(self))
		self._addRequestHandler(request.HandlerHost(self))
		self._addRequestHandler(request.HandlerJoin(self))
		self._addRequestHandler(request.HandlerLeave(self))
		self._addRequestHandler(request.HandlerEndHost(self))
		self._addRequestHandler(request.HandlerReport(self))
		self._addRequestHandler(request.HandlerRLSRegister(self))
		self._addRequestHandler(request.HandlerRLSUnRegister(self))
		self._addRequestHandler(request.HandlerRLSUpdate(self))
		self._addRequestHandler(request.HandlerRLSFullUpdate(self))
		self._addRequestHandler(request.HandlerCopyright(self))
		if __debug__:
			self._addRequestHandler(request.HandlerHelp(self))

		self._load = 0
		self._requests = 0
		self._lastloadsampletimestamp = time.time()

	def _run(self):
		(infd,outfd,errfd) = select.select([self.socket], [], [], 1.0) # timout 1s
		if self.socket in infd:
			self.handle_request()

	def _join(self):
		log(Log.INFO,"shutting down racelist server port %s:%d" % (config.servername, config.racelistport))
		self.server_close()

	def _addRequestHandler(self,handler):
		self._requesthandlers[handler.command] = handler

	def handleRequest(self,client_address,request):
		self.calcLoad()
		if len(request)==0 or len(request[0])==0:
			raise Error(Error.REQUESTERROR, "empty request")
		
		command = request[0][0]
		log(Log.INFO,"request %s from %s" % (str(request),client_address))

		if not self._requesthandlers.has_key(command):
			raise Error(Error.REQUESTERROR, "unknown command")

		return self._requesthandlers[command].handleRequest([client_address[0]]+request[0])

	def calcLoad(self):
		self._requests = self._requests + 1
		if self._requests==100:
			ct = time.time()
			self._load = 100/(ct-self._lastloadsampletimestamp)
			self._requests = 0
			self._lastloadsampletimestamp = ct
			log(Log.INFO,"current load: %s" % self._load)
# }}}

class RaceListServerRequestHandler(SocketServer.StreamRequestHandler, Middleware): # {{{

	OK = Error(Error.OK,'OK')

	def handle(self):
		log(Log.DEBUG, "connection from %s:%d" % self.client_address )

		try:
			request = self.read()
			result = self.server.handleRequest(self.client_address,request)
			self.reply(self.OK, result)
		except Error, e:
			# racelist errors are logged and sent to the client
			log(Log.ERROR,e)
			self.reply(e)
		except IOError, e:
			# something went tits up with the connection - we cant
			# help here just log and bailout
			log(Log.ERROR, e)
		except Exception, e:
			# this are errors that should not be - try to send an
			# error to the client, that something went wrong and
			# re-raise the exception again
			self.reply(Error(Error.INTERNALERROR, "internal server error"))
			raise

# }}}

class BroadCastServer(SocketServer.ThreadingUDPServer, StopableThread): # {{{
	

	def __init__(self,racelist):
		log(Log.INFO,"init broadcast server on port %s:%d" % (config.servername, config.broadcastport))

		StopableThread.__init__(self)
		
		self.racelist = racelist
		self.allow_reuse_address = 1
		SocketServer.ThreadingUDPServer.__init__(self,("",config.broadcastport),BroadCastServerRequestHandler)

	def _run(self):
		(infd,outfd,errfd) = select.select([self.socket], [], [], 1.0) # timout 1s
		if self.socket in infd:
			self.handle_request()

	def _join(self):
		log(Log.INFO,"shutting down broadcast server port %s:%d" % (config.servername, config.broadcastport))
		self.server_close()
# }}}

class BroadCastServerRequestHandler(SocketServer.DatagramRequestHandler): # {{{
	
	def handle(self):
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

class Server: # {{{
	

	def __init__(self):
		self._racelist = RaceList()
		self._serverlist = RLServerList()
		self._racelistserver = RaceListServer(self._racelist, self._serverlist)
		self._broadcastserver = BroadCastServer(self._racelist)

		self._inshutdown = 0

	def start(self):
		self._serverlist.start()
		self._racelist.start()
		self._racelistserver.start()
		self._broadcastserver.start()

	def stop(self):
		log(Log.INFO,"shutting down server");
		self._inshutdown = 1
		log(Log.INFO,"waiting for broadcast server");
		self._broadcastserver.join(1.0)
		log(Log.INFO,"waiting for racelist server");
		self._racelistserver.join(1.0)
		log(Log.INFO,"waiting for serverlist");
		self._serverlist.join()
		log(Log.INFO,"waiting for racelist");
		self._racelist.join()

	def inShutdown(self):
		return self._inshutdown!=0

# }}}

class Client(Middleware): # {{{

	def __init__(self, server='localhost', port=DEFAULT_RACELISTPORT):
		self.server_address = (server,port)

	def doLogin(self, client_uniq_id):
		result = self.doRequest([['login', request.PROTOCOL_VERSION, SERVER_VERSION, client_uniq_id]])
		self.client_id = result[0][2]
		return result

	def doRequest(self,params):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(self.server_address)
		self.rfile = s.makefile('rb')
		self.wfile = s.makefile('wb')
		self.send(params)
		self.wfile.close()
		result = self.read()
		self.rfile.close()
		s.close()
		status = Error(int(result[0][0]), result[0][1])
		if status.id <> Error.OK:
			raise status
		return result[1:]

# }}}

if __name__=="__main__": pass

# vim:fdm=marker:
