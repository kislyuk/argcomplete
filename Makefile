lint:
	./setup.py flake8

test: lint
	python test/test.py -v

init_docs:
	cd docs; sphinx-quickstart

docs:
	$(MAKE) -C docs html

install:
	python setup.py bdist_wheel
	pip install --upgrade dist/*.whl

.PHONY: test docs lint

include common.mk
