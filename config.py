#
# config module
#

from tools import log, Log

DEFAULT_RACELISTPORT=30197
DEFAULT_BROADCASTPORT=6970

configfile = 'server.conf'
servername = 'localhost'
racelistport = DEFAULT_RACELISTPORT
broadcastport = DEFAULT_BROADCASTPORT
user_timeout = 3600
race_timeout = 90
server_timeout = 90
server_update = 30
server_maxload = 3

class ConfigError(Exception):
	def __init__(self, msg):
		Exception.__init__(self,msg)

def load():
	try:
		f = open(configfile,"r")
	except IOError, e:
		raise ConfigError("Can not open config file '%s': %s" % (configfile, e))

	for line in f.readlines():

		line = line.strip()

		if len(line)==0:
			continue

		if line[0]=="#":
			continue

		if line.find("=")==-1:
			log(Log.WARNING, "Unhandled line='%s' in config file '%s'" % (line, configfile))

		key, value = line.split('=',2)
		key = key.strip()
		value = value.strip()

		try:
			if key=='servername':
				servername = value
			elif key=='racelistport':
				racelistport = int(value)
			elif key=='broadcastport':
				broadcastport = int(value)
			elif key=='user_timeout':
				user_timeout = int(value)
			elif key=='race_timeout':
				race_timeout = int(value)
			elif key=='server_timeout':
				server_timeout = int(value)
			elif key=='server_update':
				server_timeout = int(value)
			elif key=='server_maxload':
				server_timeout = int(value)
			else:
				log(Log.WARNING, "Unknown key='%s' in config file '%s'" % (key, configfile))
		except ValueError, e:
			raise ConfigError("Expect number for '%s': %s" % (key,e))
	
	if servername=='localhost':
		raise ConfigError("Use a FQDN or an IP address for the server name")

