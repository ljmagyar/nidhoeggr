VERSION=0.4

SRC=scary.tex commanddoku.tex
TARSRC=$(SRC) nidhoeggr.py Makefile
TARDIR=nidhoeggr-$(VERSION)
TARNAME=$(TARDIR).tar.gz

all:
	@echo "Nothing to do"

tar:$(TARNAME)

scary.dvi:$(SRC)
	latex $<

scary.pdf:$(SRC)
	pdflatex $<

$(TARNAME):$(TARSRC)
	mkdir $(TARDIR)
	cp $(TARSRC) $(TARDIR)
	tar cf - $(TARDIR) | gzip -c9 > $(TARNAME)
	rm -rf $(TARDIR)
