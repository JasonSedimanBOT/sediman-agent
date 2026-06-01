PAPER = main
SECTIONS = sections/abstract.tex sections/introduction.tex sections/architecture.tex \
           sections/skills.tex sections/memory.tex sections/subagents.tex \
           sections/benchmark.tex sections/related_work.tex sections/conclusion.tex

.PHONY: all clean figures watch

all: figures
	latexmk -pdf $(PAPER).tex
	latexmk -c

figures:
	python3 scripts/analyze_results.py
	python3 scripts/architecture_diagram.py

watch:
	latexmk -pdf -pvc $(PAPER).tex

clean:
	latexmk -C
	rm -f figures/*.pdf figures/*.png
