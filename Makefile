VERSION=1.1

TARSRC=Makefile scary.pdf scary.tex command_documentation.tex debugclient.py nidhoeggr.py paramchecks.py request.py server.py tools.py genhelp.py
TARDIR=nidhoeggr-$(VERSION)
TARNAME=$(TARDIR).tar.gz

all:
	@echo "Nothing to do"

doc:scary.pdf

tar:$(TARNAME)

scary.dvi:scary.tex command_documentation.tex
	latex scary.tex

scary.pdf:scary.tex command_documentation.tex
	pdflatex scary.tex

$(TARNAME):$(TARSRC)
	mkdir $(TARDIR)
	cp $(TARSRC) $(TARDIR)
	tar cf - $(TARDIR) | gzip -c9 > $(TARNAME)
	rm -rf $(TARDIR)

clean:force
	rm -f *.pyo *.pyc

force:
