# TODO
# - interface for Tom's secur to report racedata
# - interface to BigBrother
# - way to handle permanent servers
# - allow servers to have names instead of ips so dyndns entries can be used

SERVER_VERSION="nidhoeggr $Id: nidhoeggr.py,v 1.4 2004/12/12 15:19:26 ridcully Exp $"

__copyright__ = """
(c) Copyright 2003-2004 Christoph Frick <rid@zefix.tv>
(c) Copyright 2003-2004 iGOR Development Group
All Rights Reserved
This software is the proprietary information of the iGOR Development Group
Use is subject to license terms
"""
print __copyright__

from config import config, DEFAULT_RACELISTPORT

import sha
import zlib
import struct
import cPickle
import select
import random
from time import time, sleep
from threading import Semaphore

import socket; socket.setdefaulttimeout(config.sockettimeout)
from SocketServer import ThreadingTCPServer, StreamRequestHandler
from SocketServer import ThreadingUDPServer, DatagramRequestHandler

from tools import StopableThread, IdleWatcher, log, Log
import request
import paramchecks

class RaceList(StopableThread): # {{{

	STATE_START = 1
	STATE_RUN = 2
	STATE_STOP = 3

	def __init__(self, racelistserver):
		StopableThread.__init__(self,config.racelist_clean_interval)

		self._racelistserver = racelistserver

		self._users = {}
		self._usersuniqids = {}
		self._races = {}
		self._racesbroadcasts = {}
		self._reqfull = []

		self._state = RaceList.STATE_START

		self._users_sem = Semaphore(verbose=1)
		self._races_sem = Semaphore(verbose=1)
		if __debug__:
			log(Log.DEBUG, "_users_sem = %s" % self._users_sem )
			log(Log.DEBUG, "_races_sem = %s" % self._races_sem )

		self._load()

	def hasUser(self, client_id):
		return self._users.has_key(client_id)

	def hasRace(self, server_id):
		return self._races.has_key(server_id)

	def addUser(self,user):
		self._users_sem.acquire()
		try:
			client_id = user.params['client_id']
			if not self.hasUser(client_id):
				self._users[client_id] = user
				self._usersuniqids[user.params['client_uniqid']] = user
			else:
				raise Error(Error.REQUESTERROR, "user already registered")
		finally:
			self._users_sem.release()

	def removeUser(self,client_id):
		self._users_sem.acquire()
		self._races_sem.acquire()
		try:
			self._removeUser(client_id)
		finally:
			self._races_sem.release()
			self._users_sem.release()

	def _removeUser(self,client_id):
		if self.hasUser(client_id):
			if self._usersuniqids.has_key(self._users[client_id].params['client_uniqid']):
				del self._usersuniqids[self._users[client_id].params['client_uniqid']]
			del self._users[client_id]
		for race in self._races.values():
			race.removeDriver(client_id)
		self._buildRaceListAsReply()

	def getUser(self,client_id):
		self._users_sem.acquire()
		try:
			if not self.hasUser(client_id):
				raise Error(Error.AUTHERROR, "user unknown/not logged in")
			ret = self._users[client_id]
			ret.setActive()
			return ret
		finally:
			self._users_sem.release()

	def getUserByUniqId(self,client_uniqid):
		if self._usersuniqids.has_key(client_uniqid):
			return self._usersuniqids[client_uniqid]
		return None

	def addRace(self,race):
		self._races_sem.acquire()
		try:
			if not self.hasRace(race.params['server_id']):
				self._races[race.params['server_id']] = race
				self._racesbroadcasts[race.params['broadcastid']] = race
				self._buildRaceListAsReply()
		finally:
			self._races_sem.release()

	def removeRace(self,server_id,client_id):
		self._races_sem.acquire()
		try:
			self._removeRace(self, server_id, client_id)
		finally:
			self._races_sem.release()
	
	def _removeRace(self,server_id,client_id):
		if not self.hasRace(server_id):
			return
		if self._races[server_id].params['client_id']!=client_id:
			raise Error(Error.AUTHERROR, "authorization required")
		broadcastid = self._races[server_id].params['broadcastid']
		if self._racesbroadcasts.has_key(broadcastid):
			del self._racesbroadcasts[broadcastid]
		del self._races[server_id]
		self._buildRaceListAsReply()
	
	def driverJoinRace(self,server_id,driver):
		self._races_sem.acquire()
		try:
			for race in self._races.values():
				race.removeDriver(driver.params['client_id'])
			if self.hasRace(server_id):
				self._races[server_id].addDriver(driver)
				self._buildRaceListAsReply()
		finally:
			self._races_sem.release()
	
	def driverLeaveRace(self,server_id,client_id):
		self._races_sem.acquire()
		try:
			if self.hasRace(server_id):
				self._races[server_id].removeDriver(client_id)
				self._buildRaceListAsReply()
		finally:
			self._races_sem.release()

	def _buildRaceListAsReply(self):
		self.reqfull = []
		for race in self._races.values():
			if race.params['visible']:
				self.reqfull.append(race.getRaceAsReply())
				for driver in race.drivers.values():
					self.reqfull.append(driver.getDriverAsReply())

	def getRaceListAsReply(self):
		self._races_sem.acquire()
		try:
			return self.reqfull
		finally:
			self._races_sem.release()

	def updateRaceViaBroadcast(self, params):
		self._users_sem.acquire()
		self._races_sem.acquire()
		try:
			broadcastid = "%s:%s" % (params['ip'], params['joinport'])
			race = None
			if not self._racesbroadcasts.has_key(broadcastid):
				for r in self._races.values():
					if r.params['broadcastname'] == params['name']:
						# we found by name - update the ip and broadcast
						race = r
						old_broadcast_id = race.params['broadcastid']
						del self._racesbroadcasts[old_broadcast_id]
						race.params['ip'] = params['ip']
						race.genBroadcastId()
						self._racesbroadcasts[race.params['broadcastid']] = race
			else:
				race = self._racesbroadcasts[broadcastid]
			if race is not None:
				race = self._racesbroadcasts[broadcastid]
				race.updateRaceViaBroadcast(
						params['players'], 
						params['maxplayers'],
						params['racetype'], 
						params['trackdir'], 
						params['sessiontype'], 
						params['sessionleft']
				)
				self._buildRaceListAsReply()
				# set the starting user active so it gets
				# distributed for sure and assures, that a
				# race can be started on the other racelists
				client_id = race.params['client_id']
				if self._users.has_key(client_id):
					self._users[client_id].setActive()
		finally:
			self._races_sem.release()
			self._users_sem.release()

	def _run(self):
		"""lurks behind the scenes and cleans the._races and the._users"""
		# nothing do until we hit the RUN state
		if self._state!=RaceList.STATE_RUN: 
			return
		currenttime = time()
		usercount = 0
		userdelcount = 0
		racecount = 0
		racedelcount = 0
		raceinvisiblecount = 0

		self._users_sem.acquire()
		self._races_sem.acquire()
		try:
			for server_id in self._races.keys():
				racecount = racecount + 1
				# set the client, which started the race, active
				client_id = self._races[server_id].params['client_id']
				if self._users.has_key(client_id):
					self._users[client_id].setActive()
				if self._racelistserver._request_count:
					if self._races[server_id].params['visible'] and self._races[server_id].checkTimeout(currenttime):
						# soft timeout removes it from display
						if __debug__:
							log(Log.DEBUG, "setting race %s invisible" % server_id )
						self._races[server_id].params['visible'] = 0
						raceinvisiblecount = raceinvisiblecount + 1
						self._buildRaceListAsReply()
					elif self._races[server_id].checkTimeout(currenttime,config.race_timeout_hard):
						# hard timeout deletes the race
						if __debug__:
							log(Log.DEBUG, "removing race %s" % server_id )
						racedelcount = racedelcount + 1
						self._removeRace(server_id, self._races[server_id].params['client_id'])
			for client_id in self._users.keys():
				usercount = usercount + 1
				if self._users[client_id].checkTimeout(currenttime):
					if __debug__:
						log(Log.DEBUG, "removing user %s" % client_id )
					userdelcount = userdelcount + 1
					self._removeUser(client_id)
		finally:
			self._races_sem.release()
			self._users_sem.release()

		log(log.INFO, "cleanup: %d/%d users; %d/%d/%d races" % (userdelcount,usercount,racedelcount,raceinvisiblecount,racecount))
		self._save()

	def _join(self):
		self._state = RaceList.STATE_STOP
		self._save()

	def _save(self):
		"""stores the current racelist in the given file"""
		filename = config.file_racelist
		self._users_sem.acquire()
		self._races_sem.acquire()
		try:
			try:
				try:
					outf = open(filename, "w")
					cPickle.dump(self._users, outf )
					cPickle.dump(self._races, outf )
				finally:
					try: 
						outf.close()
					except:
						log(Log.WARNING,"failed to close out file for racelist: %s" % (e) )
						pass
			except Exception, e:
				log(Log.WARNING,"failed to save racelist state to file '%s': %s" % (filename,e) )
				return
		finally:
			self._races_sem.release()
			self._users_sem.release()
		log(Log.INFO, "stored racelist to file '%s'" % filename )

	def _load(self):
		"""loads the racelist from the given file"""
		filename = config.file_racelist
		log(Log.INFO, "load racelist from file '%s'" % filename )
		self._users_sem.acquire()
		self._races_sem.acquire()
		try:
			try:
				try:
					inf = open(filename, "r")
					self._users = cPickle.load(inf)
					self._races = cPickle.load(inf)
					self._racesbroadcasts = {}
					for race in self._races.values():
						self._racesbroadcasts[race.params['broadcastid']] = race
						if self._users.has_key(race.params['client_id']):
							self._users[race.params['client_id']].setActive()
						# XXX update the racelist
						race.genBroadcastId()
					self._usersuniqids = {}
					for user in self._users.values():
						self._usersuniqids[user.params['client_uniqid']] = user
				finally:
					try: inf.close()
					except: pass
			except Exception,e:
				log(Log.WARNING, "failed to load racelist state from file '%s': %s" % (filename, e) )
			self._buildRaceListAsReply()
		finally:
			self._races_sem.release()
			self._users_sem.release()
		self._state = RaceList.STATE_RUN

	def getFullUpdate(self):
		ret = []

		rq_distlogin = request.DistributedLogin()
		rq_disthost = request.DistributedHost()
		rq_join = request.Join()

		self._users_sem.acquire()
		self._races_sem.acquire()
		try:
			# add all the users of this list as distributed logins
			for user in self._users.values():
				ret.append(rq_distlogin.generateDistributableRequest(user.params))
			# add all the races of this list as distributed hosts and all
			# the drivers as joins
			for race in self._races.values():
				ret.append(rq_disthost.generateDistributableRequest(race.params))
				for driver in race.drivers.values():
					ret.append(rq_join.generateDistributableRequest(driver.params))
		finally:
			self._races_sem.release()
			self._users_sem.release()

		return ret

# }}}

class Race(IdleWatcher): # {{{
	
	def __init__(self,params):
		self.params = params
		if not self.params.has_key('server_id'):
			self.params["server_id"] = sha.new("%s%s%s%s%s" % (self.params['client_id'], self.params['ip'], self.params['joinport'], time(), random.randint(0,1000000))).hexdigest()

		self.params["sessiontype"] = 0
		self.params["sessionleft"] = self.params['praclength']
		self.params["players"]     = 0

		self.genBroadcastId()
		
		self.drivers = {}

		IdleWatcher.__init__(self,config.race_timeout)

		self._initstateless()

	def _initstateless(self):
		self.setActive()

	def genBroadcastId(self):
		firstchar = ""
		if len(self.params['firstname'])>0:
			firstchar = self.params['firstname'][0]
		self.params['broadcastname'] = "%s.%s" % (firstchar, self.params['lastname'])
		self.params["broadcastid"] = "%s:%s" % (self.params['ip'], self.params['joinport'])

	def setActive(self):
		IdleWatcher.setActive(self)
		self.params['visible'] = 1

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

	def __init__(self,params):
		self.params = params
		IdleWatcher.__init__(self, config.user_timeout)
		if not self.params.has_key('client_id'):
			self.params['client_id'] = sha.new("%s%s%s" % (params['client_uniqid'], time(), random.randint(0,1000000))).hexdigest()

# }}}

class RLServer(IdleWatcher): # {{{

	NEW = 1
	REGISTERED = 2

	def __init__(self,params):
		self.params = params
		IdleWatcher.__init__(self, config.server_timeout)
		self._initstateless()

	def _initstateless(self):
		self.requests = []
		self.setActive()
		self.state = RLServer.NEW
		self.setCurrentLoad(0)
		self.error = 0
	
	def getUpdate(self, current_load):
		self.setActive()
		self.error = 0
		self.setCurrentLoad(current_load)
		update = self.requests
		self.requests = []
		return update

	def setCurrentLoad(self, current_load):
		self.params['current_load'] = str(current_load)
		# calculate the difference between the max and the current
		# load as it will be used to sort this entry for the clients
		# in the list
		self.load_diff = int(self.params['maxload']) - current_load

	def addRequest(self, values):
		# TODO: maybe better use a max value here and then du simply a
		# full update instead of the update?
		self.requests.append(values)

	def __getstate__(self):
		return self.params

	def __setstate__(self, data):
		self.params = data
		self._initstateless()
# }}}

class RLServerList(StopableThread): # {{{

	def __init__(self,racelistserver):
		StopableThread.__init__(self,config.server_update)
		self._racelistserver = racelistserver
		# we keep ourself here
		self._rls = RLServer({
				"protocol_version":request.PROTOCOL_VERSION,
				"rls_id":sha.new("%s%s%s" % (SERVER_VERSION,config.servername,config.racelistport)).hexdigest(),
				"name":config.servername, 
				"port":str(config.racelistport), 
				"maxload":str(config.server_maxload),
				"ip":socket.gethostbyname(config.servername)
				})
		self._servers = {}
		self._servers_sem = Semaphore(verbose=1)
		if __debug__:
			log(Log.DEBUG, "_servers_sem = %s" % self._servers_sem )
		self._load()
		self.client = None

	def hasRLServer(self, rls_id):
		return self._rls.params['rls_id']==rls_id or self._servers.has_key(rls_id)

	def getRLServer(self, rls_id):
		self._servers_sem.acquire()
		try:
			if not self.hasRLServer(rls_id):
				raise Error(Error.AUTHERROR, "race list server unknown/not logged in")
			return self._servers[rls_id]
		finally:
			self._servers_sem.release()

	def addRLServer(self,rls):
		rls_id = rls.params['rls_id']
		self._servers_sem.acquire()
		try:
			# this also blocks ourself from beeing added; see hasRLServer
			if not self.hasRLServer(rls_id):
				self._servers[rls_id] = rls
		finally:
			self._servers_sem.release()
		self._buildServerListReply()

	def delRLServer(self,rls_id,ip):
		# check for unknown server
		if not self.hasRLServer(rls_id):
			return
		# check for the same ip, as the server has registered
		rls = self.getRLServer(rls_id)
		if not ip==rls.params['ip']:
			return
		# delete the server from the list
		self._servers_sem.acquire()
		try:
			del self._servers[rls_id]
		finally:
			self._servers_sem.release()
		self._buildServerListReply()

	def getUpdate(self, ip, rls_id, current_load):
		self._servers_sem.acquire()
		try:
			if self._servers.has_key(rls_id):
				rls = self._servers[rls_id]
				# update the ip of the racelist server, if it has changed
				if rls.params['ip'] != ip:
					rls.params['ip'] = ip
				ret = rls.getUpdate(current_load)
			else:
				raise Error(Error.AUTHERROR, 'unknown server')
		finally:
			self._servers_sem.release()
		# with the update comes also the current load so we rebuild the lists
		self._buildServerListReply()
		return ret

	def addRequest(self, values):
		self._servers_sem.acquire()
		try:
			for server in self._servers.values():
				server.addRequest(values)
		finally:
			self._servers_sem.release()

	def _load(self):
		filename = config.file_serverlist
		log(Log.INFO, "load the server list from file '%s'" % (filename))
		try:
			try:
				f = open(filename, "r")
				self._servers = cPickle.load(f)
			finally:
				try: f.close()
				except: pass
		except Exception, e:
			log(Log.WARNING, "failed to load server list from file '%s': %s" % (filename, e))
		self._buildServerListReply()
	
	def _save(self):
		filename = config.file_serverlist
		log(Log.INFO, "save the server list to file '%s'" % (filename))
		try:
			self._servers_sem.acquire()
			try:
				f = open(filename, "w")
				cPickle.dump(self._servers,f)
			finally:
				self._servers_sem.release()
				try: f.close()
				except: pass
		except Exception, e:
			log(Log.WARNING, "failed to save server list to file '%s': %s" % (filename, e))

	def _buildServerListReply(self):
		self._servers_sem.acquire()
		try:
			sortlist = {}
			for server in self._servers.values()+[self._rls]:
				if not sortlist.has_key(server.load_diff):
					sortlist[server.load_diff] = []
				sortlist[server.load_diff].append(server)
			slk = sortlist.keys()
			slk.sort()
			slk.reverse()
			self._simpleserverlistreply = []
			self._fullserverlistreply = []
			for load_diff in slk:
				for server in sortlist[load_diff]:
					self._simpleserverlistreply.append((server.params['name'], server.params['port']))
					self._fullserverlistreply.append((server.params['protocol_version'], server.params['rls_id'], server.params['name'], server.params['ip'], server.params['port'], server.params['maxload']))
		finally:
			self._servers_sem.release()

	def getSimpleServerListAsReply(self):
		return self._simpleserverlistreply

	def getFullServerListAsReply(self):
		return self._fullserverlistreply

	def _join(self):
		self._save()

	def registerServersFromRLRegisterResult(self, racelistserver, result):
		for row in result:
			# add the servers from the list, if they are new
			if not self.hasRLServer(row[1]):
				rls_register = request.RLSRegister()
				racelistserver.handleDistributedRequest(rls_register.generateDistributableRequest({
					'protocol_version':row[0], 
					'rls_id':row[1], 
					'name':row[2], 
					'ip':row[3], 
					'port':row[4], 
					'maxload':row[5]
				}))


	def _run(self):
		ct = time()
		changes = 0
		self._servers_sem.acquire()
		try:
			for rls in self._servers.values():
				# get the updates from the server
				try:
					client = Client(rls.params['ip'],int(rls.params['port']))
					# first register on server, that are new in the list
					if rls.state == RLServer.NEW:
						rls_register = request.RLSRegister()
						result = client.doRequest(rls_register.generateCompleteRequest(self._rls.params))
						rls.state = RLServer.REGISTERED
						self.registerServersFromRLRegisterResult(self._racelistserver, result)
						# after the registering query a full update
						rq = request.RLSFullUpdate()
					else:
						# once registered we only get updates
						rq = request.RLSUpdate()
					result = client.doRequest(rq.generateCompleteRequest(self._rls.params))
					for row in result:
						try:
							self._racelistserver.handleDistributedRequest(row)
						except Error, e:
							if e.id not in [Error.AUTHERROR, Error.NOTFOUND]:
								raise e
							log(Log.WARNING, "error on executing request - ignoring: %s" % e)
				except Exception, e:
					log(Log.ERROR, "error getting update from rls=%s - deleting: %s" % (rls.params['rls_id'],e))
					self._servers[rls.params['rls_id']].error += 1
					if self._racelistserver._request_count and self._servers[rls.params['rls_id']].error > 10:
						changes = 1
						del self._servers[rls.params['rls_id']]
					continue

				# remove the server, if it was not active for the given time
				if self._racelistserver._request_count and rls.checkTimeout(ct):
					log(Log.INFO, "dropping race list server %s (%s:%d) due to a time out" % (rls.params['rls_id'], rls.params['name'], int(rls.params['port'])))
					changes = 1
					del self._servers[rls.params['rls_id']]
		finally:
			self._servers_sem.release()
		self._racelistserver.calcLoad(ct)
		# generate the server list, if server got deleted
		if changes:
			self._buildServerListReply()
		self._save()
	
	def getInitServerList(self):
		ret = []
		ret.append([config.initserver_name,config.initserver_port])
		if len(self._servers):
			rls = self._servers.values()[0]
			ret.append([rls.params['name'],int(rls.params['port'])])
		return ret

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
	UNAVAILABLE = 503

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
	MAXSIZE=4096*1024
	CELLSEPARATOR="\001"
	ROWSEPARATOR="\002"

	def readData(self):
		clientident = self.rfile.read(4)
		if clientident!=self.CLIENTINDENT:
			raise Error(Error.REQUESTERROR, "unknown client ident")

		try:
			rawmode = self.rfile.read(1)
		except Exception,e:
			log(Log.ERROR,e)
			raise Error(Error.REQUESTERROR, "error reading mode")
		if not rawmode:
			raise Error(Error.REQUESTERROR, "error reading mode")

		mode = struct.unpack(">c", rawmode)[0]

		if mode!=self.MODE_CLEARTEXT and mode!=self.MODE_COMPRESS:
			raise Error(Error.REQUESTERROR, "unhandled mode '%s'" % (mode))
		
		try:
			rawdatasize = self.rfile.read(4)
		except Exception,e:
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
			except Exception,e:
				log(Log.ERROR,e)
				raise Error(Error.REQUESTERROR, "error reading uncompressed datasize")
			if len(rawuncompresseddatasize)!=4:
				raise Error(Error.REQUESTERROR, "error reading uncompressed datasize")

			uncompresseddatasize = struct.unpack(">L", rawuncompresseddatasize)[0]

			if uncompresseddatasize>self.MAXSIZE:
				raise Error(Error.REQUESTERROR, "unreasonable large uncompressed size=%d" %(uncompresseddatasize))

		try:
			data = self.rfile.read(datasize)
		except Exception, e:
			log(Log.ERROR,e)
			raise Error(Error.REQUESTERROR, "error reading data")

		if len(data)!=datasize:
			raise Error(Error.REQUESTERROR, "error reading data")

		if mode=="c":
			try:
				data = zlib.decompress(data)
			except Exception,e:
				log(Log.ERROR,e)
				raise Error(Error.REQUESTERROR, "error decompressing  data")

		self.rfile.close()
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
		self.wfile.close()

	def send(self,data):
		retdata = []
		for row in data:
			retdata.append(self.CELLSEPARATOR.join(row))
		self.sendData(self.ROWSEPARATOR.join(retdata))

	def reply(self,exception,data=[]):
		self.send([[str(exception.id),exception.description]]+data)

	def read(self):
		data = self.readData()
		request = []
		for row in data.split(self.ROWSEPARATOR):
			if len(row)!=0:
				request.append(row.split(self.CELLSEPARATOR))
		return request

# }}}

class RaceListServer(ThreadingTCPServer, StopableThread): # {{{

	def __init__(self):
		log(Log.INFO,"init racelist server on %s:%d" % (config.servername,config.racelistport))
		StopableThread.__init__(self)

		self._racelist = RaceList(self)
		self._serverlist = RLServerList(self)
		self._broadcastserver = BroadCastServer(self)

		self._requesthandlers = {}
		self._addRequestHandler(request.HandlerLogin(self))
		self._addRequestHandler(request.HandlerDistributedLogin(self))
		self._addRequestHandler(request.HandlerReqFull(self))
		self._addRequestHandler(request.HandlerHost(self))
		self._addRequestHandler(request.HandlerDistributedHost(self))
		self._addRequestHandler(request.HandlerJoin(self))
		self._addRequestHandler(request.HandlerLeave(self))
		self._addRequestHandler(request.HandlerEndHost(self))
		self._addRequestHandler(request.HandlerBroadcast(self))
		self._addRequestHandler(request.HandlerReport(self))
		self._addRequestHandler(request.HandlerRLSRegister(self))
		self._addRequestHandler(request.HandlerRLSUnRegister(self))
		self._addRequestHandler(request.HandlerRLSUpdate(self))
		self._addRequestHandler(request.HandlerRLSFullUpdate(self))
		self._addRequestHandler(request.HandlerCopyright(self))
		if __debug__:
			self._addRequestHandler(request.HandlerHelp(self))

		self._request_count = 0
		self._lastloadsampletimestamp = time()

		self.register()

		self.allow_reuse_address = 1
		ThreadingTCPServer.__init__(self,("",config.racelistport),RaceListServerRequestHandler)

	def start(self):
		self._serverlist.start()
		self._racelist.start()
		StopableThread.start(self)
		self._broadcastserver.start()

	def _run(self):
		try: (infd,outfd,errfd) = select.select([self.socket], [], [], 1.0) # timout 1s
		except select.error, e: log(Log.ERROR, 'error on select in racelist handler: %s' % e)
		if self.socket in infd:
			self.handle_request()

	def _join(self):
		log(Log.INFO,"waiting for broadcast server");
		self._broadcastserver.join()
		sleep(1)
		log(Log.INFO,"shutting down racelist server port %s:%d" % (config.servername, config.racelistport))
		self.server_close()
		sleep(1)
		log(Log.INFO,"waiting for serverlist");
		self._serverlist.join()
		log(Log.INFO,"waiting for racelist");
		self._racelist.join()

	def _addRequestHandler(self,handler):
		self._requesthandlers[handler.command] = handler

	def handleRequest(self,client_address,request):
		self.incRequestCount()
		if self._racelist._state!=RaceList.STATE_RUN:
			raise Error(Error.UNAVAILABLE, "racelist starts up or shuts down")
		if len(request)==0 or len(request[0])==0:
			raise Error(Error.REQUESTERROR, "empty request")
		
		command = request[0][0]
		log(Log.INFO,"request %s from %s" % (str(request),client_address))

		if not self._requesthandlers.has_key(command):
			raise Error(Error.REQUESTERROR, "unknown command")

		return self._requesthandlers[command].handleRequest([client_address[0]]+request[0])

	def handleDistributedRequest(self, request):
		log(Log.INFO,"distributed request %s" % (str(request)))
		command = request[1]
		if not self._requesthandlers.has_key(command):
			raise Error(Error.REQUESTERROR, "unknown command")
		return self._requesthandlers[command].handleDistributedRequest(request)


	def incRequestCount(self):
		self._request_count = self._request_count + 1

	def calcLoad(self, ct):
		if self._request_count>0:
			current_load = int(self._request_count/(ct-self._lastloadsampletimestamp))
		else:
			current_load = 0
		self._serverlist._rls.setCurrentLoad(current_load)
		self._request_count = 0
		self._lastloadsampletimestamp = ct
		log(Log.INFO,"current load: %s" % current_load)

	def register(self):
		success = 0
		initserverlist = self._serverlist.getInitServerList()
		for initserver in initserverlist:
			initserver_name, initserver_port = initserver
			log(Log.INFO, "registering to init server %s:%d" % (initserver_name, initserver_port))
			try:
				client = Client(initserver_name,initserver_port)
				rls_register = request.RLSRegister()
				result = client.doRequest(rls_register.generateCompleteRequest(self._serverlist._rls.params))
				self._serverlist.registerServersFromRLRegisterResult(self, result)
				success = 1
				log(Log.INFO, "success - registering to the server list from the init server")
				break
			except Exception, e:
				log(Log.WARNING, "Error on registering to init server: %s" % e)
		if not success:
			log(Log.WARNING, "failed to register to any other race list server; check your config if you are not intending to run this server as a root server" )
# }}}

class RaceListServerRequestHandler(StreamRequestHandler, Middleware): # {{{

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
			log(Log.ERROR, "IO error on handling request: %s" % e)
		except socket.error, e:
			# something went tits up with the connection - we cant
			# help here just log and bailout
			log(Log.ERROR, "socket error on handling request: %s" % e)
		except Exception, e:
			# this are errors that should not be - try to send an
			# error to the client, that something went wrong and
			# re-raise the exception again
			self.reply(Error(Error.INTERNALERROR, "internal server error"))
			raise

# }}}

class BroadCastServer(ThreadingUDPServer, StopableThread): # {{{

	def __init__(self,racelistserver):
		log(Log.INFO,"init broadcast server on port %s:%d" % (config.servername, config.broadcastport))

		StopableThread.__init__(self)
		
		self._racelistserver = racelistserver
		self.allow_reuse_address = 1
		ThreadingUDPServer.__init__(self,("",config.broadcastport),BroadCastServerRequestHandler)

	def _run(self):
		try: 
			(infd,outfd,errfd) = select.select([self.socket], [], [], 1.0) # timout 1s
			if self.socket in infd:
				self.handle_request()
		except select.error, e: 
			log(Log.ERROR, 'error on select in broadcast handler: %s' % e)

	def _join(self):
		log(Log.INFO,"shutting down broadcast server port %s:%d" % (config.servername, config.broadcastport))
		self.server_close()
# }}}

class BroadCastServerRequestHandler(DatagramRequestHandler): # {{{
	
	def handle(self):
		try:
			line = self.rfile.read(4096)
			broadcastdata = {}
			broadcastdata['version'], broadcastdata['joinport'], broadcastdata['name'], broadcastdata['trackdir'], broadcastdata['cardir'], xplayers, broadcastdata['classes'], broadcastdata['racetype'], unknown, hassession, broadcastdata['sessiontype'], timeinsession, broadcastdata['ispassworded'], broadcastdata['maxlatency'] = line[:-1].split("\001")
			broadcastdata['players'], broadcastdata['maxplayers'] = xplayers.split('/')
			if hassession=='N':
				broadcastdata['sessiontype'] = '0'
				broadcastdata['sessionleft'] = '0'
			else:
				broadcastdata['sessionleft'] = timeinsession[1:]
			rq_broadcast = request.Broadcast()
			self.server._racelistserver.handleRequest(self.client_address,rq_broadcast.generateCompleteRequest(broadcastdata))
		except Exception, e:
			# can not much do about it
			log(Log.WARNING, "Error on broadcast handling: %s" % e)

# }}}

class Server: # {{{

	def __init__(self):
		self._racelistserver = RaceListServer()
		self._inshutdown = 0

	def start(self):
		self._racelistserver.start()

	def stop(self):
		log(Log.INFO,"shutting down server");
		self._inshutdown = 1
		log(Log.INFO,"waiting for racelist server");
		self._racelistserver.join()

	def inShutdown(self):
		return self._inshutdown!=0

# }}}

class Client(Middleware): # {{{

	def __init__(self, server='localhost', port=DEFAULT_RACELISTPORT):
		self.server_address = (server,port)

	def doLogin(self, client_uniqid):
		login = request.Login()
		result = self.doRequest(login.generateCompleteRequest({'client_uniqid':client_uniqid, 'protocol_version':request.PROTOCOL_VERSION, 'client_version':SERVER_VERSION}))
		self.client_id = result[0][2]
		return result

	def doRequest(self,params):
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect(self.server_address)
			self.rfile = s.makefile('rb')
			self.wfile = s.makefile('wb')
			self.send(params)
			self.wfile.close()
			result = self.read()
			self.rfile.close()
		finally:
			try: s.close()
			except: pass
		status = Error(int(result[0][0]), result[0][1])
		if status.id <> Error.OK:
			raise status
		return result[1:]

# }}}

if __name__=="__main__": pass

# vim:fdm=marker:
