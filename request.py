import nidhoeggr
import paramchecks
import socket

PROTOCOL_VERSION="scary v0.1"

class RequestParam: # {{{
	""""""
	def __init__(self, paramname, check, help):
		self.paramname = paramname
		self.check = check
		self.help = help

	def doCheck(self,value):
		return self.check(value)
		
# }}}

class Request: # {{{
	"""defines a command for the racelist"""
	def __init__(self,command,paramconfig,description,resultdescription):
		self.command = command
		self.paramconfig = paramconfig
		self.description = description
		self.resultdescription = resultdescription
# }}}

class RequestLogin(Request): # {{{
	def __init__(self):
		Request.__init__( self,
			"login",
			[
				RequestParam("protocol_version",paramchecks.check_string,"version of the protocol, the client expects"),
				RequestParam("client_version", paramchecks.check_string, "name/version string of the client"),
				RequestParam("client_uniqid", paramchecks.check_string, "some uniq id of the client")
			],
			"""Login of the client/user onto the server. This command must be called before all others. This command will assure, that client and server speak the same version of the protocol.""",
			"""The reply contains 4 cells: protocol version, server version, client id for further requests, ip the connection came from"""
		)

# }}}

class RequestHost(Request): # {{{
	def __init__(self):
		Request.__init__( self, 
			"host", 
			[
				RequestParam("client_id", paramchecks.check_string, ""), 
				RequestParam("joinport", paramchecks.check_suint, ""), 
				RequestParam("name", paramchecks.check_string, ""), 
				RequestParam("info1", paramchecks.check_string, ""), 
				RequestParam("info2", paramchecks.check_string, ""), 
				RequestParam("comment", paramchecks.check_string, ""), 
				RequestParam("isdedicatedserver", paramchecks.check_boolean, ""),
				RequestParam("ispassworded", paramchecks.check_boolean, ""), 
				RequestParam("isbosspassworded", paramchecks.check_boolean, ""), 
				RequestParam("isauthenticedserver", paramchecks.check_boolean, ""),
				RequestParam("allowedchassis", paramchecks.check_chassisbitfield, ""),
				RequestParam("allowedcarclasses", paramchecks.check_carclassbitfield, ""),
				RequestParam("allowsengineswapping", paramchecks.check_boolean, ""),
				RequestParam("modindent", paramchecks.check_string, ""),
				RequestParam("maxlatency", paramchecks.check_suint, ""), 
				RequestParam("bandwidth", paramchecks.check_bandwidthfield, ""),
				RequestParam("maxplayers", paramchecks.check_suint, ""),
				RequestParam("trackdir", paramchecks.check_string, ""), 
				RequestParam("racetype", paramchecks.check_suint, ""), 
				RequestParam("praclength", paramchecks.check_suint, ""),
				RequestParam("aiplayers", paramchecks.check_suint, ""),
				RequestParam("numraces", paramchecks.check_suint, ""),
				RequestParam("repeatcount", paramchecks.check_suint, ""),
				RequestParam("flags", paramchecks.check_string, ""),
				RequestParam("firstname", paramchecks.check_string, ""), 
				RequestParam("lastname", paramchecks.check_string, ""), 
				RequestParam("class_id", paramchecks.check_class, ""), 
				RequestParam("team_id", paramchecks.check_team, ""), 
				RequestParam("mod_id", paramchecks.check_string, ""), 
				RequestParam("nationality", paramchecks.check_nationality, ""), 
				RequestParam("helmet_colour", paramchecks.check_helmetcolour, "")
			],
			"""Starts hosting of a race. The given informations are used to describe the race and will be displayed in the same order in the racelist.""",
			"""A unique id for the server, that will be used to update the hosting and race informations and also by the clients to join/leave the race."""
		)
# }}}

class RequestReqFull(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"req_full", 
			[
				RequestParam("client_id", paramchecks.check_string, "")
			],
			"""Returns a list of races and the drivers in this races.""",
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
		)
# }}}

class RequestJoin(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"join", 
			[
				RequestParam("server_id", paramchecks.check_string, ""), 
				RequestParam("client_id", paramchecks.check_string, ""), 
				RequestParam("firstname", paramchecks.check_string, ""), 
				RequestParam("lastname", paramchecks.check_string, ""), 
				RequestParam("class_id", paramchecks.check_class, ""), 
				RequestParam("team_id", paramchecks.check_team, ""), 
				RequestParam("mod_id", paramchecks.check_string, ""), 
				RequestParam("nationality", paramchecks.check_nationality, ""), 
				RequestParam("helmet_colour", paramchecks.check_helmetcolour, "")
			],
			"""The client with the given id joins the server with the given id. Several informations about the driver itself are also submited for the list of races and their drivers.""",
			"""Nothing."""
		)
# }}}

class RequestLeave(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"leave", 
			[
				RequestParam("server_id", paramchecks.check_string, ""), 
				RequestParam("client_id", paramchecks.check_string, "")
			],
			"""Removes the client with the given id from the server with the given id.""",
			"""Nothing."""
		)
# }}}

class RequestEndHost(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"endhost", 
			[
				RequestParam("server_id", paramchecks.check_string, ""),
				RequestParam("client_id", paramchecks.check_string, "")
			],
			"""Stops the hosting of the race with the given id.""",
			"""Nothing."""
		)
# }}}

class RequestReport(Request): # {{{
	
	def __init__(self):
		Request.__init__(self, 
			"report", 
			[
				RequestParam("server_id", paramchecks.check_string, "")
			],
			"""Updates the informations of the given server.""",
			"""Nothing."""
		)
# }}}

class RequestCopyright(Request): # {{{

	def __init__(self):
		Request.__init__(self, 
			"copyright", 
			[],
			"""Returns a copyright notice about the protocol and the server.""",
			"""String holding the text of the copyright notice."""
		)
# }}}

class RequestHelp(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"help", 
			[],
			"""Returns a list of all implemented commands.""",
			"""For each command a line starting with command, then followed by a line for each param and finally a line starting with result, explaining the data sent back to the client."""
		)
# }}}

class RequestRLSRegister(Request): # {{{

	def __init__(self):
		Request.__init__(self,
			"rls_register",
			[
				RequestParam('rls_id', paramchecks.check_string, ''),
				RequestParam('name', paramchecks.check_string, ''),
				RequestParam('port', paramchecks.check_suint, ''),
				RequestParam('maxload', paramchecks.check_maxload, '')
			],
			"""Registers a race list server for the reproduction""",
			"""List of the known race list servers"""
		)
# }}}

class RequestRLSUnRegister(Request): # {{{

	def __init__(self):
		Request.__init__(self,
			"rls_unregister",
			[
				RequestParam('rls_id', paramchecks.check_string, '')
			],
			"""Removes the race list server from the known servers""",
			"""Nothing"""
		)
# }}}

class RequestRLSUpdate(Request): # {{{

	def __init__(self):
		Request.__init__(self,
			"rls_update",
			[
				RequestParam('rls_id', paramchecks.check_string, '')
			],
			"""A list of all updates from a certain server""",
			"""List of all requests on this server since the last call of this function"""
		)
# }}}

class RequestRLSFullUpdate(Request): # {{{

	def __init__(self):
		Request.__init__(self,
			"rls_fullupdate",
			[
				RequestParam('rls_id', paramchecks.check_string, '')
			],
			"""Complete list of all data from the server; this is used after the registration to get the complete data from the choosen master""",
			"""All Users, Races and their Drivers on this server"""
		)
# }}}

class RequestHandler: # {{{

	def __init__(self,server):
		self._server = server

	def handleRequest(self,client_address,values):
		"""
		"""
		if len(self.paramconfig) != len(values):
			raise nidhoeggr.RaceListProtocolException(400,"param amount mismatch")
		params = {'ip':client_address[0]}
		for i in range(len(self.paramconfig)):
			value = values[i]
			param = self.paramconfig[i]
			checkresult = param.doCheck(value)
			if checkresult != None:
				raise nidhoeggr.RaceListProtocolException(400,"Error on %s: %s" % (param.paramname,checkresult))
			params[param.paramname] = value

		return self._handleRequest(params)

	def _handleRequest(self,data):
		raise NotImplementedError("RequestHandler._handleRequest is not implemented")

# }}}

class RequestHandlerLogin(RequestHandler, RequestLogin): # {{{
	
	def __init__(self,server):
		RequestLogin.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self,params):
		if params["protocol_version"]!=PROTOCOL_VERSION:
			if __debug__:
				raise nidhoeggr.RaceListProtocolException(400, "wrong protcol version - expected '%s'"%PROTOCOL_VERSION)
			else:
				raise nidhoeggr.RaceListProtocolException(400, "wrong protcol version")

		user = self._server._racelist.getUserByUniqId(params["client_uniqid"])
		if user is None:
			user = nidhoeggr.User(params["client_uniqid"],params['ip'])
			self._server._racelist.addUser(user)

		ret = [[PROTOCOL_VERSION,nidhoeggr.SERVER_VERSION,user.params['client_id'],user.params['outside_ip']]]
		return ret + self._server._serverlist.getServerListAsReply()

# }}}

class RequestHandlerHost(RequestHandler, RequestHost): # {{{
	"""
	"""
	def __init__(self, server):
		RequestHost.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self,params):
		self._server._racelist.getUser(params["client_id"])
		race = nidhoeggr.Race(params)
		self._server._racelist.addRace(race)

		user = self._server._racelist.getUser(params["client_id"])
		driver = nidhoeggr.Driver(user,params)
		server_id = race.params['server_id']
		self._server._racelist.driverJoinRace(server_id,driver)

		return [[server_id]]

# }}}

class RequestHandlerReqFull(RequestHandler, RequestReqFull): # {{{
	"""
	"""
	def __init__(self, server):
		RequestReqFull.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self,params):
		user = self._server._racelist.getUser(params["client_id"])
		user.setActive()
		return self._server._racelist.getRaceListAsReply()

# }}}

class RequestHandlerJoin(RequestHandler, RequestJoin): # {{{
	"""
	"""
	def __init__(self, server):
		RequestJoin.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self,params):
		user = self._server._racelist.getUser(params["client_id"])
		driver = nidhoeggr.Driver(user,params)
		self._server._racelist.driverJoinRace(params["server_id"],driver)
		return [[]]

# }}}

class RequestHandlerLeave(RequestHandler, RequestLeave): # {{{
	"""
	"""
	def __init__(self, server):
		RequestLeave.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self,params):
		self._server._racelist.driverLeaveRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class RequestHandlerEndHost(RequestHandler, RequestEndHost): # {{{
	"""
	"""
	def __init__(self, server):
		RequestEndHost.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self,params):
		self._server._racelist.removeRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class RequestHandlerReport(RequestHandler, RequestReport): # {{{
	"""
	"""
	def __init__(self, server):
		RequestReport.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self,params):
		# TODO
		raise nidhoeggr.RaceListProtocolException(501, "not yet implemented")

# }}}

class RequestHandlerCopyright(RequestHandler, RequestCopyright): # {{{
	"""
	"""
	def __init__(self, server):
		RequestCopyright.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self,params):
		return [[copyright]]

# }}}

class RequestHandlerHelp(RequestHandler, RequestHelp): # {{{

	def __init__(self, server):
		RequestHelp.__init__(self)
		RequestHandler.__init__(self, server)

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

class RequestHandlerRLSRegister(RequestHandler, RequestRLSRegister): # {{{

	def __init__(self, server):
		RequestRLSRegister.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self, params):
		server = nidhoeggr.RLServer(params)
		self._server._serverlist.addRLServer(server)
		ret = self._server._serverlist.getRealServerListAsReply()
		return ret
# }}}

class RequestHandlerRLSUnRegister(RequestHandler, RequestRLSUnRegister): # {{{

	def __init__(self, server):
		RequestRLSUnRegister.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self, params):
		ret = []
		return ret
# }}}

class RequestHandlerRLSUpdate(RequestHandler, RequestRLSUpdate): # {{{

	def __init__(self, server):
		RequestRLSUpdate.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self, params):
		ret = []
		return ret
# }}}

class RequestHandlerRLSFullUpdate(RequestHandler, RequestRLSFullUpdate): # {{{

	def __init__(self, server):
		RequestRLSFullUpdate.__init__(self)
		RequestHandler.__init__(self, server)

	def _handleRequest(self, params):
		ret = []
		return ret
# }}}

if __name__=="__main__": pass

# vim:fdm=marker:
