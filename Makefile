# Build the documentation, slides and exports.
#
# Asciidoctor runs in a container so the only hard local dependency is a
# container runtime. `make pptx` and `make test` need neither.

SHELL     := /bin/bash
BUILD     := build
DOCS      := docs/index.adoc
SLIDES    := slides/slides.adoc
PPTX      := slides/exports/redhat-ai-tax-administration.pptx
IMAGE     := docker.io/asciidoctor/docker-asciidoctor:latest
RUNTIME   := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
RUN       := $(RUNTIME) run --rm -v "$(CURDIR):/documents:z" -w /documents $(IMAGE)

.PHONY: all docs slides pptx pdf test lint labs clean help

help:
	@echo "Targets:"
	@echo "  make docs    build/docs/index.html    documentation"
	@echo "  make slides  build/slides.html        reveal.js deck"
	@echo "  make pptx    $(PPTX)"
	@echo "  make pdf     build/*.pdf              printable documentation"
	@echo "  make test    lint + run all labs in simulate mode"
	@echo "  make all     everything"

all: docs slides pptx pdf

$(BUILD):
	@mkdir -p $(BUILD)

check-runtime:
	@if [ -z "$(RUNTIME)" ]; then \
		echo "No podman or docker found."; \
		echo "Install one, or render with a local asciidoctor:"; \
		echo "  asciidoctor -D $(BUILD) $(DOCS)"; \
		exit 1; \
	fi

docs: | $(BUILD)
	@$(MAKE) --no-print-directory check-runtime
	$(RUN) asciidoctor -D $(BUILD)/docs -o index.html $(DOCS)
	@echo "-> $(BUILD)/docs/index.html"

slides: | $(BUILD)
	@$(MAKE) --no-print-directory check-runtime
	$(RUN) asciidoctor-revealjs \
		-a revealjsdir=https://cdn.jsdelivr.net/npm/reveal.js@4.6.1 \
		-D $(BUILD) -o slides.html $(SLIDES)
	@echo "-> $(BUILD)/slides.html  (press S for speaker notes)"

pdf: | $(BUILD)
	@$(MAKE) --no-print-directory check-runtime
	$(RUN) asciidoctor-pdf -D $(BUILD) \
		-o redhat-ai-tax-administration.pdf $(DOCS)
	@echo "-> $(BUILD)/redhat-ai-tax-administration.pdf"

pptx:
	python3 bin/build-pptx.py --out $(PPTX)

lint:
	@echo "Checking shell syntax..."
	@for f in bin/*.sh labs/*/run.sh; do bash -n "$$f" || exit 1; done
	@echo "Checking Python syntax..."
	@python3 -m py_compile bin/build-pptx.py labs/lab04-rag/*.py
	@echo "OK"

labs:
	./bin/run-all-labs.sh

test: lint
	@LAB_SPEED=0 NO_COLOR=1 ./bin/run-all-labs.sh

clean:
	rm -rf $(BUILD)
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
