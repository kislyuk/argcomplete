# TODO: pyflakes?
test:
	@echo "\n - Running pylint on all code"
	-pylint -E argcomplete
	@echo "\n - Running unittests"
	./test/test.py -v

flake8:
	@echo "\n - Running flake8 on all python code"
	flake8 . --max-line-length 159 --exclude=conf.py,describe_github_user.py,my_shlex.py,.tox,dist,docs,build,.git --show-source --statistics

test3:
	python3 ./test/test.py -v

release: docs
	python setup.py sdist bdist_wheel upload -s -i D2069255

docs:
	$(MAKE) -C docs html

install:
	./setup.py install

.PHONY: test release docs
