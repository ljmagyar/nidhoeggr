#!/usr/bin/python

import sys
import signal
import getopt

import nidhoeggr

def handle_shutdown(signal,frame):
	# check if the server already shuts down
	global server
	if server.inShutdown():
		print >>sys.stderr, "shutdown already in progress"
		return
	server.stop()
	sys.exit(0)

def usage(message=None,errorcode=0):
	if message is not None:
		print >>sys.stderr, message
		print >>sys.stderr, ""
	print >>sys.stderr, "Usage:\n"
	print >>sys.stderr, "\tserver -s <servername> [-w <weight>] [-r <port>] [-b <port>] [-i <fqdn or ip>] [-p <port>]\n"
	print >>sys.stderr, "-s <servername>:"
	print >>sys.stderr, "\tIP or FQDN of the server\n"
	print >>sys.stderr, "-w <weight>:"
	print >>sys.stderr, "\tweight of the server in the list - a value between 0 and 9, where 9 rates the server highest; the default is 0\n"
	print >>sys.stderr, "-r <port>:"
	print >>sys.stderr, "\tport where the racelist server is listening (default=%d)\n" % nidhoeggr.DEFAULT_RACELISTPORT
	print >>sys.stderr, "-b <port>:"
	print >>sys.stderr, "\tport where the broadcast listen server is listening (default=%d)\n" % nidhoeggr.DEFAULT_BROADCASTPORT
	print >>sys.stderr, "-i <fqdn or ip>:"
	print >>sys.stderr, "\tfqdn or ip to the init server; if not given, this instance tries to use the list from a previous run\n"
	print >>sys.stderr, "-p <port>:"
	print >>sys.stderr, "\tport of the master server; will only be used of -m is given (default=%d)\n" % nidhoeggr.DEFAULT_RACELISTPORT
	sys.exit(errorcode)

def main(argv=None):
	servername = None
	weight = 0
	initserver = None
	initserverport = nidhoeggr.DEFAULT_RACELISTPORT
	racelistport = nidhoeggr.DEFAULT_RACELISTPORT
	broadcastport = nidhoeggr.DEFAULT_BROADCASTPORT

	# check for arguments
	if argv==None:
		argv = sys.argv

	try:
		opts, args = getopt.getopt(argv[1:], "s:r:b:i:p:w:h")
	except getopt.error, msg:
		usage(msg, 1)

	for o,a in opts:
		if o in ("-h", "--help"): 
			usage()

		if o in ("-s"):
			servername = a

		if o in ("-w"):
			try:
				weight = int(a)
				assert( 0 <= weight < 10 )
			except Exception,e:
				usage("error in argument: expect value between 0 and 9 for weight (%s)" % e, 2)

		if o in ("-r"):
			try:
				racelistport = int(a)
				assert( 0 < racelistport < 65536 )
			except Exception,e:
				usage("error in argument: expect value between 1 and 65535 for raceport (%s)" % e, 2)

		if o in ("-b"):
			try:
				broadcastport = int(a)
				assert( 0 < broadcastport < 65536 )
			except Exception,e:
				usage("error in argument: expect value between 1 and 65535 for broadcastport (%s)" % e, 2)

		if o in ("-i"):
			initserver = a

		if o in ("-p"):
			try:
				initserverport = int(a)
				assert( 0 < initserverport < 65536 )
			except Exception,e:
				usage("error in argument: expect value between 1 and 65535 for initserverport (%s)" % e, 2)

	# servername is vital
	if servername is None:
		usage("missing argument: need servername - either give IP or FQDN", 2)

	# fire up the server
	global server
	server = nidhoeggr.Server(servername,weight,racelistport,broadcastport)
	server.register(initserver, initserverport)
	# set the signals the server listens on for the shutdown
	if hasattr(signal, "SIGINT"):
		signal.signal(signal.SIGINT, handle_shutdown)
	if hasattr(signal, "SIGTERM"):
		signal.signal(signal.SIGTERM, handle_shutdown)
	server.start()

if __name__=="__main__":
	sys.exit(main())

