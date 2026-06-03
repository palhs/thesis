# Test + coverage runner for the thesis simulator suites.
#
# Each suite has its own helper module (tests/nodes/_helpers.py and
# tests/network/_helpers.py are different files sharing a name), so the
# suites cannot be discovered in one pass — PYTHONPATH would collide.
# The static pattern rule below runs one suite at a time with that suite's
# directory on PYTHONPATH alongside src/.
#
#   make test                 # every suite
#   make test-pbft            # one suite (also: scheduler nodes network event_log config pos integration)
#   make coverage             # branch coverage across all suites (report-only)
#   make clean                # remove __pycache__ and coverage artifacts

PY            = python3
SUITES        = scheduler nodes network event_log config common pbft pos snowman output workload integration
SUITE_TARGETS = $(addprefix test-,$(SUITES))

.PHONY: test coverage clean $(SUITE_TARGETS)

test: $(SUITE_TARGETS)

$(SUITE_TARGETS): test-%:
	PYTHONPATH=src:tests/$* $(PY) -m unittest discover -s tests/$* -v

# Branch coverage of src/ across every suite. .coveragerc pins
# branch = True, source = src, parallel = True; each suite writes a
# .coverage.<host>.<pid>.* file, which `coverage combine` merges into a
# single .coverage for reporting. Report-only: exit status reflects the
# test run, not a coverage floor.
coverage:
	$(PY) -m coverage erase
	@for s in $(SUITES); do \
		echo "==> coverage: $$s"; \
		PYTHONPATH=src:tests/$$s $(PY) -m coverage run -m unittest discover -s tests/$$s || exit $$?; \
	done
	$(PY) -m coverage combine
	$(PY) -m coverage report

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f .coverage .coverage.* coverage.xml
	rm -rf htmlcov .pytest_cache
