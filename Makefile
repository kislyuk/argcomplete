test_deps:
	pip install coverage flake8 pexpect

lint: test_deps
	./setup.py flake8

test: lint test_deps
	coverage run --source=argcomplete ./test/test.py -v

init_docs:
	cd docs; sphinx-quickstart

docs:
	$(MAKE) -C docs html

install:
	pip install wheel
	python setup.py bdist_wheel
	pip install --upgrade dist/*.whl

.PHONY: test docs lint lint_deps

include common.mk
