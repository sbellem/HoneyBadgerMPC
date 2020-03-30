.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import sys, webbrowser

webbrowser.open("http://localhost:58888/" + sys.argv[1])
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef

export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage .coverage.*
	rm -fr htmlcov/
	rm -fr .pytest_cache/
	rm -f tests/.pytest.log

lint: ## check style with flake8
	flake8 honeybadgermpc tests

test: ## run tests quickly with the default Python
	pytest -v

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	pytest -v -n auto --cov=honeybadgermpc --cov-report term --cov-report html
	$(BROWSER) htmlcov/index.html

docs: ## generate Sphinx HTML documentation
	docker-compose run --rm honeybadgermpc make -C docs clean
	docker-compose run --rm honeybadgermpc make -C docs html O="-v -W --keep-going"
	docker-compose -f docs.yml stop viewdocs
	docker-compose -f docs.yml up -d viewdocs

servedocs: docs ## compile the docs watching for changes
	docker-compose -f docs.yml stop viewdocs
	docker-compose -f docs.yml up -d viewdocs
	$(BROWSER) index.html

release: clean ## package and upload a release
	twine upload dist/*

dist: clean ## builds source and wheel package
	python3.7 setup.py sdist bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install

ipc:
	sh scripts/launch_ipc.sh

ipc-containers:
	sh scripts/launch_ipc_containers.sh
