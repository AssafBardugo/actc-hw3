PYTEST ?= uv run python -m pytest
PYTEST_CONFIG ?= my_tests/pytest.ini


all: unit e2e

unit:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v my_tests

e2e:
	bash my_tests/end2end/test_pdf_example.sh
	bash my_tests/end2end/test_full_example.sh

.PHONY: unit e2e all