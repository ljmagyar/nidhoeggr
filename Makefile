SRC=scary.tex commanddoku.tex

scary.dvi:$(SRC)
	latex $<

scary.pdf:$(SRC)
	pdflatex $<
