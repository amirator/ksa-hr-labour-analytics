.PHONY: all run test

all: run test

run:
	python run.py

test:
	python -m pytest -q
