#!/usr/bin/env python2.2

import re

import nidhoeggr

c = nidhoeggr.Client('genhelp.py','localhost')
r = nidhoeggr.RequestSender(c,[['help']])

fw = open('command_documentation.tex','w')
fw.write( '\\section{Commands}\n\n' )
for row in r.result:
	if row[0]=='command':
		fw.write( '\\subsection{%s}\n\n' % re.sub(r'_',r'\\_',row[1]) )
		fw.write( '\\begin{description}\n' )
	elif row[0]=='description':
		fw.write( '\\item {\\it Description:}\\\\\n%s\n' % re.sub(r'_',r'\\_',row[1]) )
		fw.write( '\\item {\\it Parmameters:}\n' )
		fw.write( '\\begin{itemize}\n' )
		paramcount = 0
	elif row[0]=='parameter':
		fw.write( '\\item %s\n' % re.sub(r'_',r'\\_',row[1]) )
		paramcount = paramcount + 1
	elif row[0]=='result':
		if not paramcount:
			fw.write( '\\item None\n' )
		fw.write( '\\end{itemize}\n' )
		fw.write( '\\item {\\it Result:}\\\\\n%s\n' % re.sub(r'_',r'\\_',row[1]) )
		fw.write( '\\end{description}\n\n' )
fw.close()

