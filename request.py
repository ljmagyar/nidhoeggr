import nidhoeggr
import paramchecks
import socket

PROTOCOL_VERSION="scary v1.1"

class Param: # {{{
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

	def setParams(self,params):
		self.params = params

# }}}

class Login(Request): # {{{
	def __init__(self):
		Request.__init__( self,
			"login",
			[
				Param("protocol_version",paramchecks.check_string,"version of the protocol, the client expects"),
				Param("client_version", paramchecks.check_string, "name/version string of the client"),
				Param("client_uniqid", paramchecks.check_string, "some uniq id of the client")
			],
			"""Login of the client/user onto the server. This command must be called before all others. This command will assure, that client and server speak the same version of the protocol.""",
			"""The reply contains 4 cells: protocol version, server version, client id for further requests, ip the connection came from."""
		)

# }}}

class Host(Request): # {{{
	def __init__(self):
		Request.__init__( self, 
			"host", 
			[
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
			],
			"""Starts hosting of a race. The given informations are used to describe the race and will be displayed in the same order in the racelist.""",
			"""A unique id for the server, that will be used to update the hosting and race informations and also by the clients to join/leave the race and the IP address the request came from"""
		)
# }}}

class ReqFull(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"req_full", 
			[
				Param("client_id", paramchecks.check_string, "")
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

class Join(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"join", 
			[
				Param("server_id", paramchecks.check_string, ""), 
				Param("client_id", paramchecks.check_string, ""), 
				Param("firstname", paramchecks.check_string, ""), 
				Param("lastname", paramchecks.check_string, ""), 
				Param("class_id", paramchecks.check_class, ""), 
				Param("team_id", paramchecks.check_team, ""), 
				Param("mod_id", paramchecks.check_string, ""), 
				Param("nationality", paramchecks.check_nationality, ""), 
				Param("helmet_colour", paramchecks.check_helmetcolour, "")
			],
			"""The client with the given id joins the server with the given id. Several informations about the driver itself are also submited for the list of races and their drivers.""",
			"""Nothing."""
		)
# }}}

class Leave(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"leave", 
			[
				Param("server_id", paramchecks.check_string, ""), 
				Param("client_id", paramchecks.check_string, "")
			],
			"""Removes the client with the given id from the server with the given id.""",
			"""Nothing."""
		)
# }}}

class EndHost(Request): # {{{
	"""
	"""
	def __init__(self):
		Request.__init__(self, 
			"endhost", 
			[
				Param("server_id", paramchecks.check_string, ""),
				Param("client_id", paramchecks.check_string, "")
			],
			"""Stops the hosting of the race with the given id.""",
			"""Nothing."""
		)
# }}}

class Report(Request): # {{{
	
	def __init__(self):
		Request.__init__(self, 
			"report", 
			[
				Param("server_id", paramchecks.check_string, "")
			],
			"""Updates the informations of the given server.""",
			"""Nothing."""
		)
# }}}

class Copyright(Request): # {{{

	def __init__(self):
		Request.__init__(self, 
			"copyright", 
			[],
			"""Returns a copyright notice about the protocol and the server.""",
			"""String holding the text of the copyright notice."""
		)
# }}}

class Help(Request): # {{{
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

class RLSRegister(Request): # {{{

	def __init__(self):
		Request.__init__(self,
			"rls_register",
			[
				Param('rls_id', paramchecks.check_string, ''),
				Param('name', paramchecks.check_string, ''),
				Param('port', paramchecks.check_suint, ''),
				Param('maxload', paramchecks.check_maxload, '')
			],
			"""Registers a race list server for the reproduction""",
			"""List of the known race list servers"""
		)
# }}}

class RLSUnRegister(Request): # {{{

	def __init__(self):
		Request.__init__(self,
			"rls_unregister",
			[
				Param('rls_id', paramchecks.check_string, '')
			],
			"""Removes the race list server from the known servers""",
			"""Nothing"""
		)
# }}}

class RLSUpdate(Request): # {{{

	def __init__(self):
		Request.__init__(self,
			"rls_update",
			[
				Param('rls_id', paramchecks.check_string, '')
			],
			"""A list of all updates from a certain server""",
			"""List of all requests on this server since the last call of this function"""
		)
# }}}

class RLSFullUpdate(Request): # {{{

	def __init__(self):
		Request.__init__(self,
			"rls_fullupdate",
			[
				Param('rls_id', paramchecks.check_string, '')
			],
			"""Complete list of all data from the server; this is used after the registration to get the complete data from the choosen master""",
			"""All Users, Races and their Drivers on this server"""
		)
# }}}

class Handler: # {{{

	def __init__(self,server):
		self._server = server

	def handleRequest(self,client_address,values):
		"""
		"""
		if len(self.paramconfig) != len(values):
			raise nidhoeggr.Error(Error.REQUESTERROR,"param amount mismatch")
		params = {'ip':client_address[0]}
		for i in range(len(self.paramconfig)):
			value = values[i]
			param = self.paramconfig[i]
			checkresult = param.doCheck(value)
			if checkresult != None:
				raise nidhoeggr.Error(Error.REQUESTERROR,"Error on %s: %s" % (param.paramname,checkresult))
			params[param.paramname] = value

		return self._handleRequest(params)

	def _handleRequest(self,data):
		raise NotImplementedError("Handler._handleRequest is not implemented")

# }}}

class HandlerLogin(Handler, Login): # {{{
	
	def __init__(self,server):
		Login.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self,params):
		if params["protocol_version"]!=PROTOCOL_VERSION:
			if __debug__:
				raise nidhoeggr.Error(Error.REQUESTERROR, "wrong protcol version - expected '%s'"%PROTOCOL_VERSION)
			else:
				raise nidhoeggr.Error(Error.REQUESTERROR, "wrong protcol version")

		user = self._server._racelist.getUserByUniqId(params["client_uniqid"])
		if user is None:
			user = nidhoeggr.User(params["client_uniqid"],params['ip'])
			self._server._racelist.addUser(user)

		ret = [[PROTOCOL_VERSION,nidhoeggr.SERVER_VERSION,user.params['client_id'],user.params['outside_ip']]]
		return ret + self._server._serverlist.getSimpleServerListAsReply()

# }}}

class HandlerHost(Handler, Host): # {{{
	"""
	"""
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

		return [[server_id,params['ip']]]

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
		raise nidhoeggr.Error(Error.UNIMPLMENTED, "not yet implemented")

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

class HandlerRLSRegister(Handler, RLSRegister): # {{{

	def __init__(self, server):
		RLSRegister.__init__(self)
		Handler.__init__(self, server)
		self.serverlist = self._server._serverlist

	def _handleRequest(self, params):
		self.serverlist.addRLServer(params)
		return self.serverlist.getFullServerListAsReply()

# }}}

class HandlerRLSUnRegister(Handler, RLSUnRegister): # {{{

	def __init__(self, server):
		RLSUnRegister.__init__(self)
		Handler.__init__(self, server)
		self.serverlist = self._server._serverlist

	def _handleRequest(self, params):
		self.serverlist.delRLServer(params)
		return [[]]

# }}}

class HandlerRLSUpdate(Handler, RLSUpdate): # {{{

	def __init__(self, server):
		RLSUpdate.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params):
		ret = []
		return ret
# }}}

class HandlerRLSFullUpdate(Handler, RLSFullUpdate): # {{{

	def __init__(self, server):
		RLSFullUpdate.__init__(self)
		Handler.__init__(self, server)

	def _handleRequest(self, params):
		ret = []
		return ret
# }}}

if __name__=="__main__": pass

# vim:fdm=marker:
