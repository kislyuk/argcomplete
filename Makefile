# TODO: pyflakes?
test:
#	pylint -E argcomplete
	./test/test.py

release:
	python setup.py sdist upload -s -i D2069255

docs:
	$(MAKE) -C docs html

.PHONY: test release docs
