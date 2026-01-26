PYTEST ?= uv run python -m pytest
PYTEST_CONFIG ?= mytests/pytest.ini


all: unit bash_1 bash_2 bash_3 bash_chatgpt

unit:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v mytests

bash_1:
	mytests/end2end/test_pdf_example_1.sh

bash_2:
	mytests/end2end/test_pdf_example_2.sh

bash_3:
	mytests/end2end/test_pdf_example_3.sh

bash_chatgpt:
	mytests/end2end/chatgpt.sh

.PHONY: unit bash_1 bash_2 bash_3 bash_chatgpt all