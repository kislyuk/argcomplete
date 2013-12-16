# TODO: pyflakes?
test:
	-pylint -E argcomplete
	./test/test.py -v

test3:
	python3 ./test/test.py -v

release: docs
	python setup.py sdist upload -s -i D2069255
#	python setup.py upload_docs --upload-dir docs/_build/html -s -i D2069255

docs:
	$(MAKE) -C docs html

install:
	./setup.py install

.PHONY: test release docs
