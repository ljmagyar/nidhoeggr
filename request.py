#!/usr/bin/env python2.2

PROTOCOL_VERSION="scary v0.1"

import nidhoeggr
import paramchecks
import socket

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
				RequestParam("class_id", paramchecks.check_suint, ""), 
				RequestParam("team_id", paramchecks.check_suint, ""), 
				RequestParam("mod_id", paramchecks.check_string, ""), 
				RequestParam("nationality", paramchecks.check_suint, ""), 
				RequestParam("helmet_colour", paramchecks.check_suint, "")
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
				RequestParam("class_id", paramchecks.check_suint, ""), 
				RequestParam("team_id", paramchecks.check_suint, ""), 
				RequestParam("mod_id", paramchecks.check_string, ""), 
				RequestParam("nationality", paramchecks.check_suint, ""), 
				RequestParam("helmet_colour", paramchecks.check_suint, "")
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
	"""
	"""
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
	"""
	"""
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

class RequestHandler: # {{{
	"""
	"""

	def __init__(self,racelistserver):
		"""
		"""
		self._racelistserver = racelistserver
		self._racelist = racelistserver._racelist

	def handleRequest(self,client_address,values):
		"""
		"""
		if len(self.paramconfig) != len(values):
			raise nidhoeggr.RaceListProtocolException(400,"param amount mismatch")
		params = {'client_address':client_address}
		for i in range(len(self.paramconfig)):
			value = values[i]
			param = self.paramconfig[i]
			checkresult = param.doCheck(value)
			if checkresult != None:
				raise nidhoeggr.RaceListProtocolException(400,"Error on %s: %s" % (param.paramname,checkresult))
			params[param.paramname] = value

		return self._handleRequest(client_address,params)

	def _handleRequest(self,client_address,data):
		"""
		"""
		raise NotImplementedError("RequestHandler._handleRequest is not implemented")

# }}}

class RequestHandlerLogin(RequestHandler, RequestLogin): # {{{
	"""
	"""
	def __init__(self,racelistserver):
		RequestLogin.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		if params["protocol_version"]!=PROTOCOL_VERSION:
			if __debug__:
				raise nidhoeggr.RaceListProtocolException(400, "wrong protcol version - expected '%s'"%PROTOCOL_VERSION)
			else:
				raise nidhoeggr.RaceListProtocolException(400, "wrong protcol version")

		user = self._racelist.getUserByUniqId(params["client_uniqid"])
		if user is None:
			user = nidhoeggr.User(params["client_uniqid"],client_address[0])
			self._racelist.addUser(user)

		return [[PROTOCOL_VERSION,nidhoeggr.SERVER_VERSION,user.client_id,user.outsideip]]

# }}}

class RequestHandlerHost(RequestHandler, RequestHost): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		RequestHost.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		self._racelist.getUser(params["client_id"])
		race = nidhoeggr.Race(params)
		self._racelist.addRace(race)

		user = self._racelist.getUser(params["client_id"])
		driver = nidhoeggr.Driver(user,params)
		self._racelist.driverJoinRace(race.server_id,driver)

		return [[race.server_id]]

# }}}

class RequestHandlerReqFull(RequestHandler, RequestReqFull): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		RequestReqFull.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		user = self._racelist.getUser(params["client_id"])
		user.setActive()
		return self._racelist.getRaceListAsReply()

# }}}

class RequestHandlerJoin(RequestHandler, RequestJoin): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		RequestJoin.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		user = self._racelist.getUser(params["client_id"])
		driver = nidhoeggr.Driver(user,params)
		self._racelist.driverJoinRace(params["server_id"],driver)
		return [[]]

# }}}

class RequestHandlerLeave(RequestHandler, RequestLeave): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		RequestLeave.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		self._racelist.driverLeaveRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class RequestHandlerEndHost(RequestHandler, RequestEndHost): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		RequestEndHost.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		self._racelist.removeRace(params["server_id"], params["client_id"])
		return [[]]

# }}}

class RequestHandlerReport(RequestHandler, RequestReport): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		RequestReport.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		# TODO
		raise nidhoeggr.RaceListProtocolException(501, "not yet implemented")

# }}}

class RequestHandlerCopyright(RequestHandler, RequestCopyright): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		RequestCopyright.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		return [[copyright]]

# }}}

class RequestHandlerHelp(RequestHandler, RequestHelp): # {{{
	"""
	"""
	def __init__(self, racelistserver):
		RequestHelp.__init__(self)
		RequestHandler.__init__(self, racelistserver)

	def _handleRequest(self,client_address,params):
		ret = []
		rhs = self._racelistserver._requesthandlers.values()
		rhs.sort()
		for rh in rhs:
			ret.append(['command', rh.command])
			ret.append(['description', rh.description])
			for pc in rh.paramconfig:
				ret.append(['parameter', pc.paramname])
			ret.append(['result', rh.resultdescription])
		return ret

# }}}

# vim:fdm=marker:
