.PHONY: install-dev lint test build check clean

install-dev:
	python -m pip install -e '.[dev]'

lint:
	ruff check .

test:
	python -m unittest discover -s tests -v

build:
	python -m build

check: lint test build

clean:
	python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('build', 'dist', 'onioncall.egg-info')]"
