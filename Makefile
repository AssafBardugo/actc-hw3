PYTEST ?= uv run python -m pytest
PYTEST_CONFIG ?= mytests/pytest.ini

.PHONY: unit all

unit:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v mytests/unit_test.py

all:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v
