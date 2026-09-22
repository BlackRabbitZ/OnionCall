.PHONY: test lint format-check build check

test:
	python -m unittest discover -s tests -v

lint:
	python -m ruff check onioncall scripts tests

format-check:
	python -m ruff format --check onioncall scripts tests

build:
	python -m build

check: test lint format-check
	python -m compileall -q onioncall scripts tests
