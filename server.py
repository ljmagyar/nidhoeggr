#!/usr/bin/python

import sys
import signal
import getopt
import time

from config import config
from tools import log, Log
import nidhoeggr

server = None

def handle_shutdown(signal,frame):
	# check if the server already shuts down
	if server.inShutdown():
		log(Log.WARNING, "shutdown already in progress")
		return
	server.stop()
	sys.exit(0)

def usage(message=None,errorcode=0):
	if message is not None:
		log(Log.ERROR, message)
	log(Log.INFO, "Usage:  server [-c <configfile>]")
	log(Log.INFO, "-c <configfile>:")
	log(Log.INFO, "\tthe given file will be loaded as the config instead of the default (%s)\n" % (config.configfile))
	sys.exit(errorcode)

def main(argv=None):

	# check for arguments
	if argv==None:
		argv = sys.argv

	try:
		opts, args = getopt.getopt(argv[1:], "c:h")
	except getopt.error, msg:
		usage(msg, 1)

	for o,a in opts:
		if o in ("-h", "--help"): 
			usage()

		if o in ("-c"):
			config.configfile = a

	# load the config
	config.load()
	
	# fire up the server
	global server
	server = nidhoeggr.Server()

	# set the signals the server listens on for the shutdown
	signals = ( 'SIGHUP', 'SIGINT', 'SIGKILL', 'SIGPIPE', 'SIGALRM', 'SIGTERM', 'SIGUSR1', 'SIGUSR2' )
	for sgn in signals:
		if hasattr(signal, sgn):
			log(Log.INFO, "listening for signal '%s' for shutdown" % sgn)
			signal.signal(getattr(signal,sgn), handle_shutdown)

	# start the server and loop ad infiniti
	server.start()
	try: 
		while 1: time.sleep(1)
	except KeyboardInterrupt: 
		handle_shutdown()

if __name__=="__main__":
	sys.exit(main())

