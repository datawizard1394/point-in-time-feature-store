PYTHON ?= python3
PYTHONPATH := src
AS_OF := 2026-07-28T12:00:00Z

.PHONY: help test check demo clean

help:
	@echo "test  - run offline unit tests"
	@echo "demo  - build offline/online features and parity evidence"

test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

check:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m compileall -q src tests
	$(MAKE) test

demo:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m feature_store demo \
		--transactions data/transactions.csv \
		--observations data/observations.csv \
		--as-of $(AS_OF) \
		--output-dir .artifacts/demo

clean:
	rm -rf .artifacts
