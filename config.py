#
# config module
#

from tools import log, Log
import paramchecks

DEFAULT_RACELISTPORT=30197
DEFAULT_BROADCASTPORT=30199

class ConfigVariable:
	def __init__(self, key, default, check, cast):
		self.key = key
		self.default = default
		self.check = check
		self.cast = cast

class ConfigError(Exception):
	def __init__(self, msg):
		Exception.__init__(self,msg)

class Config:
	def __init__(self):
		self.__config_vars = {}
		self.__registerConfigVariable(ConfigVariable('configfile',                'server.conf',         paramchecks.check_string, str))
		self.__registerConfigVariable(ConfigVariable('servername',                'localhost',           paramchecks.check_string, str))
		self.__registerConfigVariable(ConfigVariable('racelistport',              DEFAULT_RACELISTPORT,  paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('broadcastport',             DEFAULT_BROADCASTPORT, paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('initserver_name',           "maserati.blw.net",    paramchecks.check_string, str))
		self.__registerConfigVariable(ConfigVariable('initserver_port',           DEFAULT_RACELISTPORT,  paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('user_timeout',              3600,                  paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('race_timeout',              300,                   paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('server_timeout',            90,                    paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('server_update',             30,                    paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('racelist_clean_interval',   60,                    paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('server_maxload',            3,                     paramchecks.check_suint,  int))
		self.__registerConfigVariable(ConfigVariable('file_racelist',             'racelist.cpickle',    paramchecks.check_string, str))
		self.__registerConfigVariable(ConfigVariable('file_serverlist',           'serverlist.cpickle',  paramchecks.check_string, str))

	def __registerConfigVariable(self,cv):
		self.__config_vars[cv.key] = cv
		setattr(self,cv.key,cv.default)

	def load(self):
		try:
			f = open(self.configfile,"r")
		except IOError, e:
			raise ConfigError("Can not open config file '%s': %s" % (self.configfile, e))

		for line in f.readlines():
			line = line.strip()
			# ignore empty line
			if len(line)==0:
				continue
			# ignore comments (leading #)
			if line[0]=="#":
				continue
			# warn about anything else, that does not contain a = char
			if line.find("=")==-1:
				log(Log.WARNING, "Unhandled line='%s' in config file '%s'" % (line, self.configfile))
			# split for key and value and trim each part of it
			key, value = line.split('=',2)
			key = key.strip()
			value = value.strip()
			# check, if the key is known
			if not self.__config_vars.has_key(key):
				log(Log.WARNING, "Unknown key='%s' in config file '%s'" % (key, self.configfile))
				continue
			# check the value
			error = self.__config_vars[key].check(value)
			if error is not None:
				log(Log.WARNING, "Invalid value %s='%s' in config file '%s': %s" % (key, value, self.configfile, error))
				continue
			# everything ok - cast and assign the value
			value = self.__config_vars[key].cast(value)
			setattr(self, key, value)
		
		if self.servername=='localhost':
			raise ConfigError("Use a FQDN or an IP address for the server name")

# singleton
config = Config()
