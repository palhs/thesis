# Test runner for the thesis simulator suites.
#
# Each suite has its own helper module (tests/nodes/_helpers.py and
# tests/network/_helpers.py are different files sharing a name), so the
# suites cannot be discovered in one pass — PYTHONPATH would collide.
# The static pattern rule below runs one suite at a time with that suite's
# directory on PYTHONPATH alongside src/.
#
#   make test                 # every suite
#   make test-integration     # one suite (also: scheduler nodes network event_log)

PY            = python3
SUITES        = scheduler nodes network event_log integration
SUITE_TARGETS = $(addprefix test-,$(SUITES))

.PHONY: test $(SUITE_TARGETS)

test: $(SUITE_TARGETS)

$(SUITE_TARGETS): test-%:
	PYTHONPATH=src:tests/$* $(PY) -m unittest discover -s tests/$* -v
