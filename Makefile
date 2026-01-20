PYTEST ?= python -m pytest
PYTEST_CONFIG ?= tests/pytest.ini

.PHONY: phase1 phase2 phase3 phase4 phase5 all

phase1:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v \
		tests/unit/phase1_*.py \
		tests/integration/phase1_*.py \
		tests/end2end/phase1_*.py

phase2:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v \
		tests/unit/phase2_*.py \
		tests/integration/phase2_*.py \
		tests/end2end/phase2_*.py

phase3:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v \
		tests/unit/phase3_*.py \
		tests/integration/phase3_*.py \
		tests/end2end/phase3_*.py

phase4:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v \
		tests/unit/phase4_*.py \
		tests/integration/phase4_*.py \
		tests/end2end/phase4_*.py

phase5:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v \
		tests/unit/phase5_*.py \
		tests/integration/phase5_*.py \
		tests/end2end/phase5_*.py

all:
	$(PYTEST) -c $(PYTEST_CONFIG) -x -v
