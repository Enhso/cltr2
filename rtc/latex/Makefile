# Two XeLaTeX passes: the second resolves the "page n/N" footer.
essay.pdf: essay.tex body.tex essay.sty $(wildcard figures/*.pdf)
	xelatex -interaction=nonstopmode -halt-on-error essay.tex > /dev/null
	xelatex -interaction=nonstopmode -halt-on-error essay.tex > /dev/null

# Redraws the four figures from rtc/research. uv supplies matplotlib and
# pandas, since the anaconda install's matplotlib does not load with NumPy 2.
figures:
	cd figures && uv run --no-project --with matplotlib --with pandas python make_figures.py

clean:
	rm -f *.aux *.log *.out

.PHONY: figures clean
