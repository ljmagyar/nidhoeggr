#!/usr/bin/env python2.2

# TODO
# - interface for Tom's secur to report racedata
# - interface to BigBrother
# - writing a client for this protocol
# - way to handle permanent servers
# - allow servers to have names instead of ips so dyndns entries can be used

SERVER_VERSION="nidhoeggr $Id: nidhoeggr.py,v 1.18 2003/10/26 20:13:01 ridcully Exp $"

DEFAULT_RACELISTPORT=27233
DEFAULT_BROADCASTPORT=6970

copyright = """
Copyright 2003 Christoph Frick <rid@zefix.tv>
Copyright 2003 iGOR Development Group
All Rights Reserved
This software is the proprietary information of the iGOR Development Group
Use is subject to license terms
"""

import sys
import sha
import zlib
import struct
import SocketServer
import random
import string
import cPickle
import re
import select
import signal
import getopt

from tools import *
import paramchecks

class RaceList(StopableThread): # {{{
	"""
	"""

	CLEANINTERVAL = 60.0 # seconds

	def __init__(self):
		"""
		"""
		StopableThread.__init__(self,self.CLEANINTERVAL)

		self._users = {}
		self._usersuniqids = {}
		self._races = {}
		self._racesbroadcasts = {}
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
				self._usersuniqids[user.client_uniqid] = user
			else:
				raise RaceListProtocolException(400, "user already registered")
		finally:
			self._users_rwlock.release_write()

	def removeUser(self,client_id):
		"""
		"""
		self._users_rwlock.acquire_write()
		try:
			if self._users.has_key(client_id):
				del self._usersuniqids[self._users[client_id].client_uniqid]
				del self._users[client_id]
		finally:
			self._users_rwlock.release_write()

	def getUser(self,client_id):
		"""
		"""
		self._users_rwlock.acquire_read()
		try:
			if not self._users.has_key(client_id):
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
			if not self._races.has_key(race.server_id):
				self._races[race.server_id] = race
				self._racesbroadcasts[race.broadcastid] = race
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
			if self._races.has_key(server_id):
				if self._races[server_id].client_id!=client_id:
					raise RaceListProtocolException(401, "authorization required")
				if self._racesbroadcasts.has_key(self._races[server_id].broadcastid):
					del self._racesbroadcasts[self._races[server_id].broadcastid]
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
			if self._races.has_key(server_id):
				self._races[server_id].addDriver(driver)
			else:
				raise RaceListProtocolException(404, "unknown server_id")
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
				raise RaceListProtocolException(404, "unknown server_id")
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

	def updateRaceViaBroadcast(self, broadcastid, players, maxplayers, trackdir, sessiontype, sessionleft):
		"""
		"""
		self._races_rwlock.acquire_write()
		try:
			if self._racesbroadcasts.has_key(broadcastid):
				self._racesbroadcasts[broadcastid].updateRaceViaBroadcast(players, maxplayers, trackdir, sessiontype, sessionleft)
				self._buildRaceListAsReply()
		finally:
			self._races_rwlock.release_write()

	def _run(self):
		"""
		lurks behind the scenes and cleans the._races and the._users
		"""
		for client_id in self._users.keys():
			if self._users[client_id].checkTimeout():
				if __debug__:
					log(Log.DEBUG, "removing user %s" % client_id )
				self.removeUser(client_id)

		for server_id in self._races.keys():
			if self._races[server_id].checkTimeout():
				if __debug__:
					log(Log.DEBUG, "removing race %s" % server_id )
				self.removeRace(server_id, self._races[server_id].client_id)

	def _join(self,filename='racelist.cpickle'):
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
			self._users = {}
			for user in self._users.values():
				self._usersuniqids[user.client_uniqid] = user
		except Exception,e:
			log(Log.WARNING, "failed to load racelist state from file '%s': %s" % (filename, e) )
		self._buildRaceListAsReply()

# }}}

class Race(IdleWatcher): # {{{
	"""
	"""
	
	def __init__(self,params):
		"""
		"""
		self.params = params
		self.params["ip"] = self.client_address[0]
		self.params["server_id"] = sha.new("%s%s%s%s%s" % (self.client_id,self.ip, self.joinport, time.time(), random.randint(0,1000000))).hexdigest()
		self.params["broadcastid"] = "%s:%s" % (self.ip, self.joinport)

		self.params["sessiontype"] = 0
		self.params["sessionleft"] = self.praclength
		self.params["players"]     = 0
		
		self.drivers = {}

		self._initstateless()

	def _initstateless(self):
		"""
		"""
		IdleWatcher.__init__(self,900.0)
		self._rwlock = ReadWriteLock()

	def addDriver(self,driver):
		"""
		"""
		self._rwlock.acquire_write()
		self.setActive()
		try:
			if not self.drivers.has_key(driver.client_id):
				self.drivers[driver.client_id] = driver
			# silently ignore the request, if this driver has already joined the race
		finally:
			self._rwlock.release_write()

	def removeDriver(self,client_id):
		"""
		"""
		self._rwlock.acquire_write()
		self.setActive()
		try:
			if self.drivers.has_key(client_id):
				del self.drivers[client_id]
			# silently ignore the request, if there is not driver with this id in the race
		finally:
			self._rwlock.release_write()
			
	def updateRaceViaBroadcast(self, players, maxplayers, trackdir, sessiontype, sessionleft):
		"""
		"""
		self._rwlock.acquire_write()
		self.setActive()
		try:
			self.players     = players
			self.maxplayers  = maxplayers
			self.trackdir    = trackdir
			self.sessiontype = sessiontype
			self.sessionleft = sessionleft
		finally:
			self._rwlock.release_write()

	def getRaceAsReply(self):
		"""
		"""
		self._rwlock.acquire_read()
		try:
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
				str(self.players),
				str(self.maxplayers),
				str(self.trackdir),
				str(self.racetype),
				str(self.praclength),
				str(self.sessiontype),
				str(self.sessionleft),
				str(self.aiplayers),
				str(self.numraces),
				str(self.repeatcount),
				str(self.flags)
			)
		finally:
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

class User(IdleWatcher): # {{{
	"""
	"""

	def __init__(self,client_uniqid,outsideip):
		"""
		"""
		IdleWatcher.__init__(self, 3600.0)

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
	def __init__(self,id,description):
		Exception.__init__(self, description)
		self.id = id
		self.description = description

# }}}

# class RaceListRequestParam: # {{{
# 	""""""
# 	def __init__(self, paramname, check, help):
# 		self.paramname = paramname
# 		self.check = check
# 		self.help = help
# 	def doCheck(self,value):
# 		
# 
# class RaceListRequest: # {{{
# 	"""defines a command for the racelist"""
# 	def __init__(self,command,paramconfig):
# 		self.command = command
# 		self.paramconfig = paramconfig
# # }}}

class RaceListRequestHandler: # {{{
	"""
	"""
	PROTOCOL_VERSION="scary v0.1"

	def __init__(self,racelistserver,command,paramconfig):
		"""
		"""
		self.command = command
		self.paramconfig = paramconfig
		self._racelistserver = racelistserver
		self._racelist = racelistserver._racelist
		self._keys = []
		self._checks = []
		for param in paramconfig:
			(paramname,type) = string.split(param,":")
			checkname = 'check_%s'%type
			if not hasattr(paramchecks,checkname):
				raise Exception("Unknown check for type=%s"%type)
			self._keys.append(paramname)
			self._checks.append(getattr(paramchecks,checkname))

	def handleRequest(self,client_address,values):
		"""
		"""
		if len(self._keys) != len(values):
			raise RaceListProtocolException(400,"param amount mismatch (expecting: %s)"%self._keys)
		params = {'client_address':client_address}
		for i in range(len(self._keys)):
			value = values[i]
			key = self._keys[i]
			check = self._checks[i]
			checkresult = check(value)
			if checkresult != None:
				raise RaceListProtocolException(400,"Error on %s: %s" % (key,checkresult))
			params[key] = value

		return self._handleRequest(client_address,params)

	def _handleRequest(self,client_address,data):
		"""
		"""
		raise NotImplementedError("RaceListRequestHandler._handleRequest is not implemented")

# }}}

class RaceListRequestHandlerLogin(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self,racelistserver):
		"""Login of the client/user onto the server. This command must be called before all others. This command will assure, that client and server speak the same version of the protocol."""
		RaceListRequestHandler.__init__(self, racelistserver, "login", [
			"protocol_version:string",
			"client_version:string",
			"client_uniqid:string"
		])

	def _handleRequest(self,client_address,params):
		"""The reply contains 4 cells: protocol version, server version, client id for further requests, ip the connection came from"""
		if params["protocol_version"]!=self.PROTOCOL_VERSION:
			if __debug__:
				raise RaceListProtocolException(400, "wrong protcol version - expected '%s'"%self.PROTOCOL_VERSION)
			else:
				raise RaceListProtocolException(400, "wrong protcol version")

		user = self._racelist.getUserByUniqId(params["client_uniqid"])
		if user is None:
			user = User(params["client_uniqid"],client_address[0])
			self._racelist.addUser(user)

		return [[self.PROTOCOL_VERSION,SERVER_VERSION,user.client_id,user.outsideip]]

# }}}

class RaceListRequestHandlerHost(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		"""Starts hosting of a race. The given informations are used to describe the race and will be displayed in the same order in the racelist."""
		RaceListRequestHandler.__init__(self, racelistserver, "host", [
			"client_id:string", 
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
			"praclength:suint",
			"aiplayers:suint",
			"numraces:suint",
			"repeatcount:suint",
			"flags:string",
			"firstname:string", 
			"lastname:string", 
			"class_id:suint", 
			"team_id:suint", 
			"mod_id:string", 
			"nationality:suint", 
			"helmet_colour:suint"
		])

	def _handleRequest(self,client_address,params):
		"""A unique id for the server, that will be used to update the hosting and race informations and also by the clients to join/leave the race."""
		self._racelist.getUser(params["client_id"])
		race = Race(params)
		self._racelist.addRace(race)

		user = self._racelist.getUser(params["client_id"])
		driver = Driver(user,params)
		self._racelist.driverJoinRace(race.server_id,driver)

		return [[race.server_id]]

# }}}

class RaceListRequestHandlerReqFull(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		"""Returns a list of races and the drivers in this races."""
		RaceListRequestHandler.__init__(self, racelistserver, "req_full", [
			"client_id:string"
		])

	def _handleRequest(self,client_address,params):
		"""The complete current racelist. Each line holds either a race or following the drivers of a race. Each line starts either with a cell containing R or D. Races consist of the following: 
			
		R, 
		server_id, 
		ip, 
		joinport, 
		name, 
		info1, 
		info2, 
		comment, 
		isdedicatedserver, 
		ispassworded, 
		isbosspassworded, 
		isauthenticedserver, 
		allowedchassis, 
		allowedcarclasses, 
		allowsengineswapping, 
		modindent, 
		maxlatency, 
		bandwidth, 
		players,
		maxplayers, 
		trackdir, 
		racetype, 
		praclength, 
		sessionleft, 
		sessiontype,
		aiplayers,
		numraces,
		repeatcount,
		flags


		The drivers contain this data:

		D,
		firstname,
		lastname,
		class_id,
		team_id,
		mod_id,
		nationality,
		helmet_colour,
		qualifying_time,
		race_position,
		race_laps,
		race_notes
		"""

		user = self._racelist.getUser(params["client_id"])
		user.setActive()
		return self._racelist.getRaceListAsReply()

# }}}

class RaceListRequestHandlerJoin(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		"""The client with the given id joins the server with the given id. Several informations about the driver itself are also submited for the list of races and their drivers."""
		RaceListRequestHandler.__init__(self, racelistserver, "join", [
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
		"""Nothing."""
		user = self._racelist.getUser(params["client_id"])
		driver = Driver(user,params)
		self._racelist.driverJoinRace(params["server_id"],driver)
		return [[]]

# }}}

class RaceListRequestHandlerLeave(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		"""Removes the client with the given id from the server with the given id."""
		RaceListRequestHandler.__init__(self, racelistserver, "leave", [
			"server_id:string", 
			"client_id:string"
		])

	def _handleRequest(self,client_address,params):
		"""Nothing."""
		self._racelist.driverLeaveRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class RaceListRequestHandlerEndHost(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		"""Stops the hosting of the race with the given id."""
		RaceListRequestHandler.__init__(self, racelistserver, "endhost", [
			"server_id:string",
			"client_id:string"
		])

	def _handleRequest(self,client_address,params):
		"""Nothing."""
		self._racelist.removeRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class RaceListRequestHandlerReport(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		"""Updates the informations of the given server."""
		RaceListRequestHandler.__init__(self, racelistserver, "report", [
			"server_id:string"
		])

	def _handleRequest(self,client_address,params):
		"""Nothing."""
		# TODO
		raise RaceListProtocolException(501, "not yet implemented")

# }}}

class RaceListRequestHandlerCopyright(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		"""Returns a copyright notice about the protocol and the server."""
		RaceListRequestHandler.__init__(self, racelistserver, "copyright", [])

	def _handleRequest(self,client_address,params):
		"""String holding the text of the copyright notice."""
		return [[copyright]]

# }}}

class RaceListRequestHandlerHelp(RaceListRequestHandler): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		"""Returns a list of all implemented commands."""
		RaceListRequestHandler.__init__(self, racelistserver, "help", [])

	def _handleRequest(self,client_address,params):
		"""For each command a line starting with command, then followed by a line for each param and finally a line starting with result, explaining the data sent back to the client."""
		ret = []
		rhs = self._racelistserver._requesthandlers.values()
		rhs.sort()
		for rh in rhs:
			ret.append(['command', rh.command])
			ret.append(['description', rh.__init__.__doc__])
			for pc in rh.paramconfig:
				ret.append(['parameter', pc])
			ret.append(['result', rh._handleRequest.__doc__])
		return ret

# }}}

class RaceListServer(SocketServer.ThreadingTCPServer): # {{{
	"""
	"""

	def __init__(self,racelistport=DEFAULT_RACELISTPORT,broadcastport=DEFAULT_BROADCASTPORT):
		"""
		"""
		print copyright
		log(Log.INFO,"init %s on port %d" % (SERVER_VERSION,racelistport))
		
		self.allow_reuse_address = 1
		SocketServer.ThreadingTCPServer.__init__(self,("",racelistport),RaceListServerRequestHandler)

		self._racelist = RaceList()

		self._broadcastserver = RaceListBroadCastServer(self._racelist,broadcastport)

		self._requesthandlers = {}
		self._addRequestHandler(RaceListRequestHandlerLogin(self))
		self._addRequestHandler(RaceListRequestHandlerReqFull(self))
		self._addRequestHandler(RaceListRequestHandlerHost(self))
		self._addRequestHandler(RaceListRequestHandlerJoin(self))
		self._addRequestHandler(RaceListRequestHandlerLeave(self))
		self._addRequestHandler(RaceListRequestHandlerEndHost(self))
		self._addRequestHandler(RaceListRequestHandlerReport(self))
		self._addRequestHandler(RaceListRequestHandlerCopyright(self))
		self._addRequestHandler(RaceListRequestHandlerHelp(self))

		# get the help and write it into an tex file
		if __debug__:
			fw = open('commanddoku.tex','w')
			fw.write( '\\section{Commands}\n\n' )
			for row in self.handleRequest(('127.0.0.1',1024), string.join([ "help" ],'\001')):
				if row[0]=='command':
					fw.write( '\\subsection{%s}\n\n' % re.sub(r'_',r'\\_',row[1]) )
					fw.write( '\\begin{description}\n' )
				elif row[0]=='description':
					fw.write( '\\item {\\it Description:}\\\\\n%s\n' % re.sub(r'_',r'\\_',row[1]) )
					fw.write( '\\item {\\it Parmameters:}\n' )
					fw.write( '\\begin{itemize}\n' )
					paramcount = 0
				elif row[0]=='parameter':
					fw.write( '\\item %s\n' % re.sub(r'_',r'\\_',row[1]) )
					paramcount = paramcount + 1
				elif row[0]=='result':
					if not paramcount:
						fw.write( '\\item None\n' )
					fw.write( '\\end{itemize}\n' )
					fw.write( '\\item {\\it Result:}\\\\\n%s\n' % re.sub(r'_',r'\\_',row[1]) )
					fw.write( '\\end{description}\n\n' )
			fw.close()

	def _addRequestHandler(self,handler):
		"""
		"""
		self._requesthandlers[handler.command] = handler

	def handleRequest(self,client_address,data):
		"""
		"""
		requestdata = data.split("\001")
		if len(requestdata)==0:
			raise RaceListProtocolException(400, "empty request")
		
		requestname = requestdata[0]
		if __debug__:
			log(Log.DEBUG,"request: "+str(requestdata))

		if not self._requesthandlers.has_key(requestname):
			raise RaceListProtocolException(400, "unknown command")
		return self._requesthandlers[requestname].handleRequest(client_address,requestdata[1:])

	def startServer(self):
		"""
		"""
		self._racelist.start()
		self._broadcastserver.start()
		self.serve_forever()

	def stopServer(self):
		"""
		"""
		log(Log.INFO,"shutting down server");
		log(Log.INFO,"waiting for broadcast server");
		self._broadcastserver.join()
		log(Log.INFO,"waiting for racelist");
		self._racelist.join()

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
			self.sendResult([200,'OK'],result)
		except RaceListProtocolException, e:
			# racelist errors are logged and sent to the client
			log(Log.ERROR,e)
			self.sendError(e)
		except IOError, e:
			# something went wrong with the connection - we cant
			# help here just log and bailout
			log(Log.ERROR, e)
		except Exception, e:
			# this are error that should not be - try to send an
			# error to the client, that something went wrong and
			# re-raise the exception again
			self.sendError(RaceListProtocolException(500, "internal server error"))
			raise

	def readMessage(self):
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
		self.sendResult([exception.id,exception.description],[])

	def sendResult(self,status,reply):
		result = "%d%s%s" % (status[0],self.CELLSEPARATOR,status[1])
		for list in reply:
			result += "%s%s" % (self.ROWSEPARATOR,string.join(list,self.CELLSEPARATOR))
		self.writeMessage(result)


# }}}

class RaceListBroadCastServer(SocketServer.ThreadingUDPServer, StopableThread): # {{{
	"""
	"""

	def __init__(self,racelist,broadcastport=DEFAULT_BROADCASTPORT):
		"""
		"""
		log(Log.INFO,"init broadcast listen server on port %d" % (broadcastport))

		StopableThread.__init__(self)
		
		self.racelist = racelist
		self.allow_reuse_address = 1
		SocketServer.ThreadingUDPServer.__init__(self,("",broadcastport),RaceListBroadCastServerRequestHandler)

	def _run(self):
		"""
		"""
		(infd,outfd,errfd) = select.select([self.socket], [], [], 1.0) # timout 1s
		if self.socket in infd:
			self.handle_request()
# }}}

class RaceListBroadCastServerRequestHandler(SocketServer.DatagramRequestHandler): # {{{
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

			if __debug__:
				log(Log.DEBUG, "got ping info: broadcastid=%s players=%s maxplayers=%s trackdir=%s sessiontype=%s sessionleft=%s" % (broadcastid, players, maxplayers, trackdir, sessiontype, sessionleft))
			self.server.racelist.updateRaceViaBroadcast(broadcastid, players, maxplayers, trackdir, sessiontype, sessionleft)
		except Exception, e:
			# can not much do about it
			log(Log.DEBUG, e)

# }}}

def handle_shutdown(signal,frame):
	global server
	server.stopServer()
	sys.exit(0)

def main(argv=None):
	if argv==None:
		argv = sys.argv
	try:
		racelistport = DEFAULT_RACELISTPORT
		broadcastport = DEFAULT_BROADCASTPORT

		try:
			opts, args = getopt.getopt(argv[1:], "r:b:h")
		except getopt.error, msg:
			raise Exception(msg)

		for o,a in opts:
			if o in ("-h", "--help"): 
				print >>sys.stderr, "Usage:"
				print >>sys.stderr, "%s [-r <port>] [-b <port>]" % argv[0]
				print >>sys.stderr, "-r <port>: port where the racelist server is listening (default=%d)" % DEFAULT_RACELISTPORT
				print >>sys.stderr, "-b <port>: port where the broadcast listen server is listening (default=%d)" % DEFAULT_BROADCASTPORT
				return 0

			if o in ("-r", "--racelistport"):
				try:
					racelistport = string.atoi(a)
					assert( 0 < racelistport < 65536 )
				except Exception,e:
					raise Exception("expect value between 1 and 65535 for raceport (%s)" % e)

			if o in ("-b", "--broadcastport"):
				try:
					broadcastport = string.atoi(a)
					assert( 0 < broadcastport < 65536 )
				except Exception,e:
					raise Usage("expect value between 1 and 65535 for broadcastport (%s)" % e)
	except Exception, err:
		print >>sys.stderr, err
		print >>sys.stderr, "For help use -h"
		return 2
	
	global server 
	server = RaceListServer(racelistport,broadcastport)
	signal.signal(signal.SIGINT, handle_shutdown)
	signal.signal(signal.SIGTERM, handle_shutdown)
	signal.signal(signal.SIGKILL, handle_shutdown)
	server.startServer()

if __name__=="__main__":
	sys.exit(main())

# vim:fdm=marker
