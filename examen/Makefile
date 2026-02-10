# Makefile for LaTeX article compilation

LATEX = pdflatex
BIBTEX = bibtex
MAIN = article
OUTPUT_DIR = build

.PHONY: all clean view

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex
	@echo "Compiling LaTeX document..."
	$(LATEX) $(MAIN).tex
	$(LATEX) $(MAIN).tex
	@echo "PDF generated: $(MAIN).pdf"

clean:
	@echo "Cleaning up auxiliary files..."
	rm -f $(MAIN).aux $(MAIN).log $(MAIN).out $(MAIN).bbl $(MAIN).blg $(MAIN).toc
	@echo "Clean complete"

cleanall: clean
	@echo "Removing PDF..."
	rm -f $(MAIN).pdf
	@echo "All files removed"

view: $(MAIN).pdf
	@echo "Opening PDF..."
	open $(MAIN).pdf

help:
	@echo "Available targets:"
	@echo "  all      - Compile the LaTeX document (default)"
	@echo "  clean    - Remove auxiliary files"
	@echo "  cleanall - Remove all generated files including PDF"
	@echo "  view     - Open the PDF file"
	@echo "  help     - Show this help message"
