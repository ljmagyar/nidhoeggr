VERSION=0.5

TARSRC=Makefile scary.pdf scary.tex commands.tex debugclient.py nidhoeggr.py paramchecks.py request.py server.py tools.py
TARDIR=nidhoeggr-$(VERSION)
TARNAME=$(TARDIR).tar.gz

all:
	@echo "Nothing to do"

tar:$(TARNAME)

scary.tex:commands.tex

scary.dvi:scary.tex
	latex scary.tex

scary.pdf:scary.tex
	pdflatex scary.tex

$(TARNAME):$(TARSRC)
	mkdir $(TARDIR)
	cp $(TARSRC) $(TARDIR)
	tar cf - $(TARDIR) | gzip -c9 > $(TARNAME)
	rm -rf $(TARDIR)
