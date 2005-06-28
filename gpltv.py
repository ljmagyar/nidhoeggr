from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack

CLOSE_CONNECTION  = 0x00
CAR_POSITION_DATA = 0x02
CHAT_MESSAGES     = 0x03
DRIVER_INFO       = 0x04
RACE_INFO         = 0x05
SERVER_NAME       = 0x06
STANDINGS_INFO    = 0x07

#
# Messag handlers
#

def readCString(msg, offset):
	"""reads a C string (\0 terminated) and returns the string and the next offset
	"""
	soffset = offset
	while not msg[soffset]=="\000":
		soffset += 1
	return (msg[offset:soffset], soffset+1)


class Message:
	"""base class for all messages
	"""

	def __init__(self, id, msg):
		self.id = id
		self.msg = msg

	def _commonInfo(self, messagename=""):
		return "Message '%s' from %s (%s:%d)" % (messagename, self.server.servername, self.server.ip, self.server.port)


class MessageUnhandled(Message):
	"""helper class to also allow unhandled messages, but tell the
	   consumers that this data are not turned into something use full by
	   a handler
	"""


class MessageCloseConnection(Message):
	"""detects, that the server has closed the connection
	"""

	WRONG_PASSWORD             = 0x01
	NUMBER_OF_CLIENTS_EXCEEDED = 0x02

	names = {
		WRONG_PASSWORD : "Wrong Password",
		NUMBER_OF_CLIENTS_EXCEEDED  : "Number Of CLients Exceeded"
	}

	def __init__(self, msg):
		Message.__init__(self, CLOSE_CONNECTION, msg)
		self.reason = ord(msg[0])

	def __str__(self):
		return "%s\nreason:\t%s (%d)" % (self._commonInfo("Close Connection"), MessageCloseConnection.names[self.reason], self.reason)


class MessageChatMessage(Message):
	"""simple chat messages, sent from one driver to all drivers
	"""

	def __init__(self, msg):
		Message.__init__(self, CHAT_MESSAGES, msg)
		self.message = msg

	def __str__(self):
		return "%s\nmessage:\t'%s'" % (self._commonInfo("Chat Message"), self.message)


class MessageServerName(Message):
	"""notification about the name of the server
	"""

	def __init__(self, msg):
		Message.__init__(self, SERVER_NAME, msg)
		self.servername = msg

	def __str__(self):
		return "%s\nmessage:\t'%s'" % (self._commonInfo("Server Name"), self.servername)


class MessageRaceInfo(Message):
	"""update about the race in progress
	"""

	def __init__(self, msg):
		Message.__init__(self, RACE_INFO, msg)

		o = 0

		self.trackdir, o = readCString(msg, o)

		self.carset, o = readCString(msg, o)

		self.race_type = ord(msg[o])
		o += 1

		self.race_laps = ord(msg[o])


class MessageDriverInfo(Message):
	"""update about a certain driver, that can be related to a standings
	   info using the car_number
	"""

	def __init__(self, msg):
		Message.__init__(self, DRIVER_INFO, msg)

		o = 0

		self.first_name, o = readCString(msg, o)

		self.last_name, o = readCString(msg, o)

		self.car_type = ord(msg[o])
		o += 1

		self.car_number = ord(msg[o])
		o += 1

		self.start_number = ord(msg[o])

class MessageStandingsInfo(Message):
	"""update about the times of a driver; this can be related to the
	   driver using the car_number of the driver info
	"""

	def __init__(self, msg):
		Message.__init__(self, STANDINGS_INFO, msg)

		self.car_number = ord(msg[0]) & 0x7F
		self.in_race = ord(msg[0]) & 0x8F == 0x8F

		self.lap_number = ord(msg[1])

		self.clear_standings = self.car_number==127 and self.lap_number==255

		self.time1 = unpack("<I", msg[2:5])[0]
		self.time2 = unpack("<I", msg[6:9])[0]

#
# BASE DATA
#

class Driver:
	"""general data collection representing the current state of a driver
	   within a race
	"""

	def __init__(self, msg):
		self.first_name = msg.first_name
		self.last_name = msg.last_name
		self.car_type = msg.car_type
		self.car_number = msg.car_number
		self.start_number = msg.start_number
		self.clearStandings()

	def clearStandings(self):
		self.lap_number = -1
		self.time1 = -1
		self.time2 = -1

	def updateByStandingsInfo(self, msi):
		self.lap_number = msi.lap_number
		self.time1 = msi.time1
		self.time2 = msi.time2


class Race:
	"""general collection of all data known about a race
	"""

	def __init__(self, trackdir):
		self.trackdir = trackdir
		self.in_race = 0
		self.drivers = {}

	def updateByRaceInfo(self, mri):
		self.trackdir = msi.trackdir
		self.carset = msi.carset
		self.race_type = msi.race_type
		self.race_laps = msi.race_laps

	def updateByDriverInfo(self, mdi):
		self.drivers[driver.car_number] = Driver(driver)

	def updateByStandingsInfo(self, msi):
		# check for a change in the session
		if msi.in_race != self.in_race:
			self.in_race = msi.in_race
			self.clearStandings()
		# if this is the "fake" player/lapnumber, we need to clear
		# standings too
		if msi.clear_standings:
			self.clearStandings()
		else:
			# otherwise check, if we know the driver and then
			# update it
			if not self.drivers.has_key(msi.car_number):
				return
			self.drivers[msi.car_number].updateByStandingsInfo(msi)

	def clearStandings(self):
		for driver in self.drivers.values():
			driver.clearStandings()

#
# SERVER HANDLING
#

class Server:
	"""informations about one server with the ability to connect to this
	   server and use the handler to get message representations of the
	   data received from it
	"""

	DEFAULTPORT = 32002

	_CONNECT   = "GPL.tv connect:%s\000"
	_SIGNATURE = "GPL.tv"

	handler = {
		CLOSE_CONNECTION : MessageCloseConnection,
		CHAT_MESSAGES : MessageChatMessage,
		SERVER_NAME : MessageServerName,
		RACE_INFO : MessageRaceInfo,
		DRIVER_INFO : MessageDriverInfo,
		STANDINGS_INFO : MessageStandingsInfo
	}

	def __init__(self, ip, port=DEFAULTPORT, servername=None, trackdir=None, reserved=None):
		self.ip = ip
		self.port = port
		self.servername = servername
		self.reserved = reserved
		self.connected = 0
		self.race = Race(trackdir)

	def __str__(self):
		return "gpl.tv server\n=============\nHost:\t%s:%d\nName:\t%s\nTrack:\t%s\nRvd:\t%s" % (self.ip, self.port, self.servername, self.race.trackdir, self.reserved)

	def connect(self, password=""):
		self.socket = socket(AF_INET, SOCK_STREAM)
		self.socket.connect((self.ip, self.port))
		self.socket.send(Server._CONNECT % password)
		self.connected = 1

	def disconnect(self):
		self.socket.close()
		self.connected = 0

	def handle(self):
		signature = self.socket.recv(6)
		assert(signature==Server._SIGNATURE)

		id = ord(self.socket.recv(1)[0])
		len = ord(self.socket.recv(1)[0]) * 4

		msg = self.socket.recv(len)
		
		if self.handler.has_key(id):
			# get the message ...
			message = self.handler[id](msg)
			# ... and see, if we have to act on it
			if id == CLOSE_CONNECTION:
				self.disconnect()
			elif id == SERVER_NAME:
				self.servername = message.servername
			elif id == RACE_INFO:
				self.race.updateByRaceInfo(message)
			elif id == DRIVER_INFO:
				self.race.updateByDriverInfo(message)
			elif id == STANDINGS_INFO:
				self.race.updateByStandingsInfo(message)

			return message

		# if there where no handler return a dummy message - maybe the consumer can handle it
		return MessageUnhandled(id, msg)


class MetaServer:
	"""meta server, that keeps a list of servers; it is configured to
	   query the default meta server
	"""

	DEFAULTHOST = "vr-7.de"
	DEFAULTPORT = 32002

	_GETLIST = "GPL.tv get server list\000"

	def __init__(self, hostname=DEFAULTHOST, port=DEFAULTPORT):
		self.hostname = hostname
		self.port = port

	def query(self):

		ret = []

		s = socket(AF_INET, SOCK_STREAM)
		s.connect((self.hostname, self.port))
		s.send(MetaServer._GETLIST)

		while 1:
			server = self._query(s)
			if server:
				ret.append(server)
			else:
				break
		return ret

	def _query(self, s):
		msglen = s.recv(1)
		if not msglen: 
			return None
		msglen = ord(msglen[0])
		if msglen==0:
			return None

		msg = s.recv(msglen)

		offset = 0
		servername, offset = readCString(msg, offset)

		trackdir, offset = readCString(msg, offset)

		ip = "%u.%u.%u.%u" % tuple(map(ord,msg[offset:offset+4]))
		offset += 4

		port = unpack("<H", msg[offset:offset+2])[0]
		offset += 2

		reserved = map(ord, msg[offset:offset+5])
		offset += 5

		assert(offset==msglen)

		return Server(ip, port, servername, trackdir, reserved)


#
# MAIN
#

def main(args=[]):
	"""sample debug code: query all servers from the meta server, connect
	   to each one of them and print debug output of all the messages
	   received
	"""
	from select import select
	select_infds = {}
	metaserver = MetaServer()
	for gpltvserver in metaserver.query():
		print gpltvserver
		gpltvserver.connect()
		select_infds[gpltvserver.socket.fileno()] = gpltvserver
	while 1: 
		outfds, infds, errfds = select([], select_infds.keys(), [])
		for infd in infds:
			message = select_infds[infd].handle()
			if message:
				print message

if __name__ == "__main__":
	import sys
	main(sys.argv)
