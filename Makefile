ifeq ($(OS),Windows_NT)
    ACTIVATE:=.venv/Scripts/activate
else
    ACTIVATE:=.venv/bin/activate
endif

UV:=$(shell uv --version)
ifdef UV
	VENV:=uv venv
	PIP:=uv pip
else
	VENV:=python -m venv
	PIP:=python -m pip
endif

.venv:
	$(VENV) .venv

.PHONY: setup
setup: .venv
	source $(ACTIVATE) && $(PIP) install -Ue .[dev,test]

.PHONY: test
test:
	python -m coverage run -m pytest $(TESTOPTS)
	python -m coverage report

.PHONY: format
format:
	ruff format
	ruff check --fix

.PHONY: lint
lint:
	ruff check
	python -m checkdeps --allow-names moreorless moreorless
	mypy --strict --install-types --non-interactive moreorless
