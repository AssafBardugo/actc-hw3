PYTEST ?= uv run python -m pytest
PYTEST_CONFIG ?= mytests/pytest.ini


all: unit integration

unit:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v \
	mytests/unit/test_store.py	\
	mytests/unit/test_controllers.py

integration:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v \
	mytests/integration/test_api.py


.PHONY: unit integration all