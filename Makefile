test: lint
	python setup.py test -v

lint_deps:
	pip install flake8

lint: lint_deps
	python setup.py flake8 -v
#	flake8 . --max-line-length 159 --exclude=conf.py,describe_github_user.py,my_shlex.py,.tox,dist,docs,build,.git --show-source --statistics

release: docs
	python setup.py sdist bdist_wheel upload -s -i D2069255

docs:
	$(MAKE) -C docs html

install:
	./setup.py install

.PHONY: test lint lint_deps release docs
