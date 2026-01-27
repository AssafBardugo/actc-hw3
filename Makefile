PYTEST ?= uv run python -m pytest
PYTEST_CONFIG ?= my_tests/pytest.ini


all: unit bash_1 bash_2 bash_3 bash_chatgpt

unit:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v my_tests

bash_1:
	my_tests/end2end/test_pdf_example_1.sh

bash_2:
	my_tests/end2end/test_pdf_example_2.sh

bash_3:
	my_tests/end2end/test_pdf_example_3.sh

bash_chatgpt:
	my_tests/end2end/chatgpt.sh

.PHONY: unit bash_1 bash_2 bash_3 bash_chatgpt all