import nidhoeggr
import paramchecks

PROTOCOL_VERSION="scary v1.1"

class Param: # {{{
	def __init__(self, paramname, check, help):
		self.paramname = paramname
		self.check = check
		self.help = help

	def doCheck(self,value):
		return self.check(value)
		
# }}}

class Request: # {{{
	distributable = 0
	command = None
	paramconfig = None
	description = None
	resultdescription = None

	def __init__(self): pass

	def generateRequest(self, params):
		ret = [self.command]
		for pc in self.paramconfig:
			ret.append(params[pc.paramname])
		return ret

	def generateCompleteRequest(self, params):
		return [self.generateRequest(params)]

	def generateDistributableRequest(self, params):
		return [params['ip']] + self.generateRequest(params)

# }}}

class DistributableRequest(Request): # {{{
	distributable = 1

# }}}

class Login(Request): # {{{
	command ="login"
	paramconfig = [
		Param("protocol_version",paramchecks.check_string,"version of the protocol, the client expects"),
		Param("client_version", paramchecks.check_string, "name/version string of the client"),
		Param("client_uniqid", paramchecks.check_string, "some uniq id of the client")
	]
	description = """Login of the client/user onto the server. This command must be called before all others. This command will assure, that client and server speak the same version of the protocol."""
	resultdescription = """The reply contains 4 cells: protocol version, server version, client id for further requests, ip the connection came from."""

# }}}

class DistributedLogin(Request): # {{{
	command = "distributedlogin"
	paramconfig = [
		Param("client_id",paramchecks.check_string,"the client_id a client got assigned from the server it logged in"),
	] + Login.paramconfig
	description = """This command is only distributed to the other race list servers; its similar to the Login command but contains the client_id the client got assigned from the server"""
	resultdescription = """Nothing"""

# }}}

class Host(Request): # {{{
	command = "host"
	paramconfig = [
		Param("client_id", paramchecks.check_string, ""), 
		Param("joinport", paramchecks.check_suint, ""), 
		Param("name", paramchecks.check_string, ""), 
		Param("info1", paramchecks.check_string, ""), 
		Param("info2", paramchecks.check_string, ""), 
		Param("comment", paramchecks.check_string, ""), 
		Param("isdedicatedserver", paramchecks.check_boolean, ""),
		Param("ispassworded", paramchecks.check_boolean, ""), 
		Param("isbosspassworded", paramchecks.check_boolean, ""), 
		Param("isauthenticedserver", paramchecks.check_boolean, ""),
		Param("allowedchassis", paramchecks.check_chassisbitfield, ""),
		Param("allowedcarclasses", paramchecks.check_carclassbitfield, ""),
		Param("allowsengineswapping", paramchecks.check_boolean, ""),
		Param("modindent", paramchecks.check_string, ""),
		Param("maxlatency", paramchecks.check_suint, ""), 
		Param("bandwidth", paramchecks.check_bandwidthfield, ""),
		Param("maxplayers", paramchecks.check_players, ""),
		Param("trackdir", paramchecks.check_string, ""), 
		Param("racetype", paramchecks.check_racetype, ""), 
		Param("praclength", paramchecks.check_suint, ""),
		Param("aiplayers", paramchecks.check_players, ""),
		Param("numraces", paramchecks.check_suint, ""),
		Param("repeatcount", paramchecks.check_suint, ""),
		Param("flags", paramchecks.check_string, ""),
		Param("firstname", paramchecks.check_string, ""), 
		Param("lastname", paramchecks.check_string, ""), 
		Param("class_id", paramchecks.check_class, ""), 
		Param("team_id", paramchecks.check_team, ""), 
		Param("mod_id", paramchecks.check_string, ""), 
		Param("nationality", paramchecks.check_nationality, ""), 
		Param("helmet_colour", paramchecks.check_helmetcolour, "")
	]
	description = """Starts hosting of a race. The given informations are used to describe the race and will be displayed in the same order in the racelist."""
	resultdescription = """A unique id for the server, that will be used to update the hosting and race informations and also by the clients to join/leave the race and the IP address the request came from"""

# }}}

class DistributedHost(Request): # {{{
	command = "distributedhost"
	paramconfig = [
		Param("server_id", paramchecks.check_string, ""), 
	] + Host.paramconfig
	description = """This command is only distributed to the other race list servers; its similar to the Host command but contains the server_id the hosting client got assigned from the server"""
	resultdescription = """Nothing"""

# }}}

class Join(DistributableRequest): # {{{
	command = "join"
	paramconfig = [
		Param("server_id", paramchecks.check_string, ""), 
		Param("client_id", paramchecks.check_string, ""), 
		Param("firstname", paramchecks.check_string, ""), 
		Param("lastname", paramchecks.check_string, ""), 
		Param("class_id", paramchecks.check_class, ""), 
		Param("team_id", paramchecks.check_team, ""), 
		Param("mod_id", paramchecks.check_string, ""), 
		Param("nationality", paramchecks.check_nationality, ""), 
		Param("helmet_colour", paramchecks.check_helmetcolour, "")
	]
	description = """The client with the given id joins the server with the given id. Several informations about the driver itself are also submited for the list of races and their drivers."""
	resultdescription = """Nothing."""
	
# }}}

class Leave(DistributableRequest): # {{{
	command = "leave"
	paramconfig = [
		Param("server_id", paramchecks.check_string, ""), 
		Param("client_id", paramchecks.check_string, "")
	]
	description = """Removes the client with the given id from the server with the given id."""
	resultdescription = """Nothing."""

# }}}

class EndHost(DistributableRequest): # {{{
	command = "endhost"
	paramconfig = [
		Param("server_id", paramchecks.check_string, ""),
		Param("client_id", paramchecks.check_string, "")
	]
	description = """Stops the hosting of the race with the given id."""
	resultdescription = """Nothing."""
 
# }}}

class ReqFull(Request): # {{{
	command = "req_full"
	paramconfig = [
		Param("client_id", paramchecks.check_string, "")
	]
	description = """Returns a list of races and the drivers in this races."""
	resultdescription = """The complete current racelist. Each line holds either a race or following the drivers of a race. Each line starts either with a cell containing R or D. Races consist of the following: 
		
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

# }}}

class Report(Request): # {{{
	command = "report"
	paramconfig = [
		Param("server_id", paramchecks.check_string, "")
	]
	description = """Updates the informations of the given server."""
	resultdescription = """Nothing."""
 
# }}}

class Copyright(Request): # {{{
	command = "copyright"
	paramconfig = []
	description = """Returns a copyright notice about the protocol and the server."""
	resultdescription = """String holding the text of the copyright notice."""

# }}}

class Help(Request): # {{{
	command = "help"
	paramconfig = []
	description = """Returns a list of all implemented commands."""
	resultdescription = """For each command a line starting with command, then followed by a line for each param and finally a line starting with result, explaining the data sent back to the client."""

# }}}

class Broadcast(DistributableRequest): # {{{
	command ="broadcast"
	paramconfig = [
		Param("version",paramchecks.check_string,""),
		Param("joinport",paramchecks.check_suint,""),
		Param("name",paramchecks.check_string,""),
		Param("trackdir",paramchecks.check_string,""),
		Param("cardir",paramchecks.check_string,""),
		Param("players",paramchecks.check_players,""),
		Param("maxplayers",paramchecks.check_players,""),
		Param("racetype",paramchecks.check_string,""),
		Param("classes",paramchecks.check_string,""),
		Param("sessiontype",paramchecks.check_sessiontype,""),
		Param("sessionleft",paramchecks.check_suint,""),
		Param("ispassworded",paramchecks.check_string,""),
		Param("maxlatency",paramchecks.check_suint,"")
	]
	description = """Broadcast from a race server."""
	resultdescription = """none."""

# }}}

class RLSRegister(Request): # {{{
	command = "rls_register"
	paramconfig = [
		Param('protocol_version', paramchecks.check_string, 'version of the protocol, the server expects'),
		Param('rls_id', paramchecks.check_string, ''),
		Param('name', paramchecks.check_string, ''),
		Param('port', paramchecks.check_suint, ''),
		Param('maxload', paramchecks.check_maxload, '')
	]
	description = """Registers a race list server for the reproduction"""
	resultdescription = """List of the known race list servers"""

# }}}

class RLSUnRegister(Request): # {{{
	command = "rls_unregister"
	paramconfig = [
		Param('rls_id', paramchecks.check_string, '')
	]
	description = """Removes the race list server from the known servers"""
	resultdescription = """Nothing"""

# }}}

class RLSUpdate(Request): # {{{
	command = "rls_update"
	paramconfig = [
		Param('rls_id', paramchecks.check_string, ''),
		Param('current_load', paramchecks.check_maxload, '')
	]
	description = """A list of all updates from a certain server"""
	resultdescription = """List of all requests on this server since the last call of this function"""

# }}}

class RLSFullUpdate(Request): # {{{
	command = "rls_fullupdate"
	paramconfig = [
		Param('rls_id', paramchecks.check_string, '')
	]
	description = """Complete list of all data from the server; this is used after the registration to get the complete data from the choosen master"""
	resultdescription = """All Users, Races and their Drivers on this server"""

# }}}

class Handler: # {{{

	def __init__(self,server):
		self._server = server

	def handleRequest(self,values):
		params = self._paramsFromValues(values)
		if self.distributable:
			self._server._serverlist.addRequest(values)
		return self._handleRequest(params)

	def handleDistributedRequest(self, values):
		params = self._paramsFromValues(values)
		return self._handleDistributedReqest(params)

	def _paramsFromValues(self, values):
		if len(self.paramconfig) != len(values)-2:
			raise nidhoeggr.Error(nidhoeggr.Error.REQUESTERROR,"param amount mismatch")
		params = {}
		checkresult = paramchecks.check_ip(values[0])
		if checkresult != None:
			raise nidhoeggr.Error(nidhoeggr.Error.INTERNALERROR,"client address malformed")
		params['ip'] = values[0]
		for i in range(len(self.paramconfig)):
			value = values[i+2]
			param = self.paramconfig[i]
			checkresult = param.doCheck(value)
			if checkresult != None:
				raise nidhoeggr.Error(nidhoeggr.Error.REQUESTERROR,"Error on %s: %s" % (param.paramname,checkresult))
			params[param.paramname] = value
		return params

	def _handleRequest(self,data): pass

	def _handleDistributedReqest(self,data):
		self._handleRequest(data)

# }}}

class HandlerLogin(Handler, Login): # {{{
	
	def __init__(self,server):
		Login.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		if params["protocol_version"]!=PROTOCOL_VERSION:
			if __debug__:
				raise nidhoeggr.Error(nidhoeggr.Error.REQUESTERROR, "wrong protcol version - expected '%s'"%PROTOCOL_VERSION)
			else:
				raise nidhoeggr.Error(nidhoeggr.Error.REQUESTERROR, "wrong protcol version")

		user = self._server._racelist.getUserByUniqId(params["client_uniqid"])
		if user is None:
			user = nidhoeggr.User(params)
			self._server._racelist.addUser(user)
			dl = DistributedLogin()
			params['client_id'] = user.params['client_id']
			self._server._serverlist.addRequest(dl.generateDistributableRequest(params))

		ret = [[PROTOCOL_VERSION,nidhoeggr.SERVER_VERSION,user.params['client_id'],user.params['ip']]]
		return ret + self._server._serverlist.getSimpleServerListAsReply()

	def _handleDistributedReqest(self, params): pass

# }}}

class HandlerDistributedLogin(Handler, DistributedLogin): # {{{
	
	def __init__(self,server):
		DistributedLogin.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params): pass

	def _handleDistributedReqest(self,params):
		user = self._server._racelist.getUserByUniqId(params["client_uniqid"])
		if user is None:
			user = nidhoeggr.User(params)
			self._server._racelist.addUser(user)

# }}}

class HandlerHost(Handler, Host): # {{{

	def __init__(self, server):
		Host.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		self._server._racelist.getUser(params["client_id"])
		race = nidhoeggr.Race(params)
		self._server._racelist.addRace(race)

		user = self._server._racelist.getUser(params["client_id"])
		driver = nidhoeggr.Driver(user,params)
		server_id = race.params['server_id']
		self._server._racelist.driverJoinRace(server_id,driver)

		dh = DistributedHost()
		params['server_id'] = server_id
		self._server._serverlist.addRequest(dh.generateDistributableRequest(params))

		return [[server_id,params['ip']]]

# }}}

class HandlerDistributedHost(Handler, DistributedHost): # {{{

	def __init__(self, server):
		DistributedHost.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params): pass

	def _handleDistributedReqest(self,params):
		user = self._server._racelist.getUser(params["client_id"])

		race = nidhoeggr.Race(params)
		self._server._racelist.addRace(race)

		driver = nidhoeggr.Driver(user,params)
		server_id = race.params['server_id']
		self._server._racelist.driverJoinRace(server_id,driver)

# }}}

class HandlerReqFull(Handler, ReqFull): # {{{
	"""
	"""
	def __init__(self, server):
		ReqFull.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		user = self._server._racelist.getUser(params["client_id"])
		user.setActive()
		return self._server._racelist.getRaceListAsReply()

# }}}

class HandlerJoin(Handler, Join): # {{{
	"""
	"""
	def __init__(self, server):
		Join.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		user = self._server._racelist.getUser(params["client_id"])
		driver = nidhoeggr.Driver(user,params)
		self._server._racelist.driverJoinRace(params["server_id"],driver)
		return [[]]

# }}}

class HandlerLeave(Handler, Leave): # {{{
	"""
	"""
	def __init__(self, server):
		Leave.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		self._server._racelist.driverLeaveRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class HandlerEndHost(Handler, EndHost): # {{{
	"""
	"""
	def __init__(self, server):
		EndHost.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		self._server._racelist.removeRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class HandlerReport(Handler, Report): # {{{
	"""
	"""
	def __init__(self, server):
		Report.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		# TODO
		raise nidhoeggr.Error(nidhoeggr.Error.UNIMPLMENTED, "not yet implemented")

# }}}

class HandlerCopyright(Handler, Copyright): # {{{
	"""
	"""
	def __init__(self, server):
		Copyright.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		return [[copyright]]

# }}}

class HandlerHelp(Handler, Help): # {{{

	def __init__(self, server):
		Help.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		ret = []
		rhs = self._server._requesthandlers.values()
		rhs.sort()
		for rh in rhs:
			ret.append(['command', rh.command])
			ret.append(['description', rh.description])
			for pc in rh.paramconfig:
				ret.append(['parameter', pc.paramname, pc.help])
			ret.append(['result', rh.resultdescription])
		return ret

# }}}

class HandlerBroadcast(Handler, Broadcast): # {{{
	
	def __init__(self, server):
		Broadcast.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params):
		self._server._racelist.updateRaceViaBroadcast(params)
		return []
# }}}

class HandlerRLSRegister(Handler, RLSRegister): # {{{

	def __init__(self, server):
		RLSRegister.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params):
		if params["protocol_version"]!=PROTOCOL_VERSION:
			if __debug__:
				raise nidhoeggr.Error(nidhoeggr.Error.REQUESTERROR, "wrong protcol version - expected '%s'"%PROTOCOL_VERSION)
			else:
				raise nidhoeggr.Error(nidhoeggr.Error.REQUESTERROR, "wrong protcol version")
		if not self._server._serverlist.hasRLServer(params['rls_id']):
			rls = nidhoeggr.RLServer(params)
			self._server._serverlist.addRLServer(rls)
		return self._server._serverlist.getFullServerListAsReply()

# }}}

class HandlerRLSUnRegister(Handler, RLSUnRegister): # {{{

	def __init__(self, server):
		RLSUnRegister.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params):
		self._server._serverlist.delRLServer(params['rls_id'], params['ip'])
		return [[]]

# }}}

class HandlerRLSUpdate(Handler, RLSUpdate): # {{{

	def __init__(self, server):
		RLSUpdate.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params):
		return self._server._serverlist.getUpdate(params['ip'], params['rls_id'], int(params['current_load']))
# }}}

class HandlerRLSFullUpdate(Handler, RLSFullUpdate): # {{{

	def __init__(self, server):
		RLSFullUpdate.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params):
		return self._server._racelist.getFullUpdate()
# }}}

if __name__=="__main__": pass

# vim:fdm=marker:
