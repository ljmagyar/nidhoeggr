#!/usr/bin/env python

import sys
import signal
import getopt
import time

from config import config
from tools import log, Log
import nidhoeggr

server = None

def handleShutdownSignal(signal,frame):
	handleShutdown()

def handleShutdown():
	# check if the server already shuts down
	if server.inShutdown():
		log(Log.WARNING, "shutdown already in progress")
		return
	server.stop()
	sys.exit(0)
	return

def usage(message=None,errorcode=0):
	if message is not None:
		log(Log.ERROR, message)
	log(Log.INFO, "Usage:  server [-c <configfile>]")
	log(Log.INFO, "-c <configfile>:")
	log(Log.INFO, "\tthe given file will be loaded as the config instead of the default (%s)\n" % (config.configfile))
	sys.exit(errorcode)
	return

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

	log(Log.INFO, "installing signal handlers")
	# set the signals the server listens on for ignoring them
	ignoresignals = ( 'SIGPIPE', 'SIGALRM', 'SIGUSR1', 'SIGUSR2' )
	for sgn in ignoresignals:
		if hasattr(signal, sgn):
			log(Log.INFO, "ignoring signal '%s'" % sgn)
			signal.signal(getattr(signal,sgn), signal.SIG_IGN)

	# set the signals the server listens on for the shutdown
	shutdownsignals = ( 'SIGHUP', 'SIGINT', 'SIGTERM' )
	for sgn in shutdownsignals:
		if hasattr(signal, sgn):
			log(Log.INFO, "shutdown on signal '%s'" % sgn)
			signal.signal(getattr(signal,sgn), handleShutdownSignal)

	# start the server and loop ad infiniti
	server.start()
	try: 
		while 1: time.sleep(1)
	except KeyboardInterrupt: 
		handleShutdown()

if __name__=="__main__":
	sys.exit(main())

