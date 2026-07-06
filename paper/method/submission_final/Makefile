MAIN=critical_boundary_calibration_final

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex refs.bib figures/*.png
	latexmk -pdf -interaction=nonstopmode -halt-on-error $(MAIN).tex

clean:
	latexmk -C $(MAIN).tex
