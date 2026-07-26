# Tests

A labpack is where the rig-specific code lives, so it is also where rig-specific mistakes live, and
those are the ones that cost an experiment. This directory is here so a lab has somewhere to put
tests for its own protocols and drivers rather than discovering problems at the microscope.

Run them with:

```shell
pip install -e .[test]
pytest
```

What is worth testing without any hardware attached is more than it first appears. `hid`, `nidaqmx`
and `labjack` can be stubbed out and the *bytes* a driver would send checked against the
manufacturer's documentation — see `test_dlpc350_pattern_mode.py`, which verifies the projector's
pattern LUT without a projector. A LUT with its fields in the wrong bits still validates and still
plays; it just displays something other than what was meant, which is exactly the kind of error
that is invisible until someone analyses the data.

Protocols can be checked too, and `stimpack --check-labpack --deep` already does much of it: it
imports every protocol, runs it against a recording manager, and reports stimulus names that will
not resolve and calls addressed nowhere. Worth running before an experiment, not after.

Mark anything that genuinely needs the rig with `@pytest.mark.hardware` so it stays out of CI.
