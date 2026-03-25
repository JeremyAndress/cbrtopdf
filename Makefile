.PHONY: build publish release

build:
	poetry build

publish:
	poetry publish

release: build publish
