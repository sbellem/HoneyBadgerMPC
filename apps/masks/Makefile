.PHONY: clean clean-test clean-pyc clean-build docs help

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef

export PRINT_HELP_PYSCRIPT



help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-pyc

clean-pyc: ## remove Python file artifacts
	docker-compose run --no-deps --rm mpcnet find . -name '*.pyc' -exec rm -f {} +
	docker-compose run --no-deps --rm mpcnet find . -name '*.pyo' -exec rm -f {} +
	docker-compose run --no-deps --rm mpcnet find . -name '*~' -exec rm -f {} +
	docker-compose run --no-deps --rm mpcnet find . -name '__pycache__' -exec rm -fr {} +

rm-dbs:
	docker-compose run --no-deps --rm mpcnet rm -rf apps/masks/db*

down: ## stop and remove containers, networks, images, and volumes
	docker-compose down

down-sim: ## stop and remove containers, networks, images, and volumes
	docker-compose -f sim.yml down

stop:
	docker-compose stop blockchain mpcnet

rm:
	docker-compose rm --stop --force blockchain setup mpcnet client

run: down rm clean ## run the example
	docker-compose up -d blockchain
	docker-compose up setup
	docker-compose up -d client
	sh follow-logs-with-tmux.sh

run-without-tmux: rm clean ## run the example
	docker-compose up -d blockchain
	docker-compose up setup
	docker-compose up -d client
	docker-compose logs --follow blockchain mpcnet client

run-sim: down rm clean ## run the example
	docker-compose -f sim.yml up -d eth.blockchain.io
	docker-compose -f sim.yml up hbmpc.coordinator.io
	docker-compose -f sim.yml up -d hbmpc.client.io
	sh follow-sim-logs-with-tmux.sh

setup: rm clean
	docker-compose up -d blockchain
	docker-compose up setup
	docker-compose rm --stop --force blockchain
