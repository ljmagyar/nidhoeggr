#!/usr/bin/env python

import re

import nidhoeggr

if __name__!="__main__": pass

c = nidhoeggr.Client()
c.doLogin('genhelp.py')
result = c.doRequest([['help']])

fw = open('command_documentation.tex','w')
fw.write( '\\section{Commands}\n\n' )
for row in result:
	if row[0]=='command':
		fw.write( '\\subsection{%s}\n\n' % re.sub(r'_',r'\\_',row[1]) )
		fw.write( '\\begin{description}\n' )
	elif row[0]=='description':
		fw.write( '\\item {\\it Description:}\\\\\n%s\n' % re.sub(r'_',r'\\_',row[1]) )
		fw.write( '\\item {\\it Parmameters:}\n' )
		fw.write( '\\begin{itemize}\n' )
		paramcount = 0
	elif row[0]=='parameter':
		fw.write( '\\item {\\tt %s}: %s\n' % (re.sub(r'_',r'\\_', row[1]), row[2]) )
		paramcount = paramcount + 1
	elif row[0]=='result':
		if not paramcount:
			fw.write( '\\item None\n' )
		fw.write( '\\end{itemize}\n' )
		fw.write( '\\item {\\it Result:}\\\\\n%s\n' % re.sub(r'_',r'\\_',row[1]) )
		fw.write( '\\end{description}\n\n' )
fw.close()

