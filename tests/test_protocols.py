"""The protocols' client-side logic, checked without a rig.

Two things are covered here, both of the kind that fails silently on a rig:

- every protocol class constructs from a bare config, so a typo in an __init__ or a parameter
  default is caught by CI rather than by the GUI's protocol dropdown at the start of an experiment;

- the pieces of lab logic that never run on this machine during an experiment -- LinearTrack's
  server-side trial-ending condition (it runs in the server process) and BaseProtocol's
  voltage_out helper (its dropped branch only matters on a rig without the hardware) -- which is
  exactly why a test is the only place they get exercised before they matter.

`stimpack --check-labpack --deep` constructs and runs every protocol too; these tests additionally
pin down behavior the checker has no opinion on (which trial-ending value wins, how often the
helper warns).
"""
import inspect
from unittest import mock

import pytest

from template_labpack.protocol import JohnDoe_protocol as protocols
from template_labpack.protocol.base_protocol import BaseProtocol


def protocol_classes():
    """Every concrete protocol class in JohnDoe_protocol.py. The file's own BaseProtocol is the
    lab-wide intermediate, not a runnable protocol, so it is excluded by name -- the same
    convention the GUI relies on."""
    return [cls for _, cls in inspect.getmembers(protocols, inspect.isclass)
            if issubclass(cls, BaseProtocol) and cls.__module__ == protocols.__name__
            and cls.__name__ != 'BaseProtocol']


# --- every protocol constructs -------------------------------------------------------------------

@pytest.mark.parametrize('protocol_class', protocol_classes(), ids=lambda c: c.__name__)
def test_protocol_constructs_from_a_bare_config(protocol_class):
    """An empty cfg is what the protocol sees before a rig is chosen; construction must survive it."""
    protocol = protocol_class(cfg={})
    assert protocol.run_parameters, 'run parameter defaults came back empty'
    assert protocol.protocol_parameters, 'protocol parameter defaults came back empty'


# --- LinearTrack: the trial ends where the track does --------------------------------------------
#
# server_side_state_dependent_control runs on the SERVER, per tracker update, with two dicts:
# state_update (what the tracker just reported) and subject_state (the accumulated state as it was
# BEFORE this update). The distinction is the whole trap -- see the behavior-ended trials guide.

def control(subject_state, state_update):
    """Run the control function against a recording server; returns (server_mock, returned_update)."""
    server = mock.MagicMock()
    returned = protocols.LinearTrack.server_side_state_dependent_control(
        server, subject_state, state_update)
    return server, returned


def test_reaching_the_end_ends_the_trial_with_a_reason():
    server, _ = control(subject_state={'y': 0.0},
                        state_update={'y': protocols.LinearTrack.TRACK_LENGTH + 0.01})
    server.end_trial.assert_called_once_with(reason='reached_track_end')


def test_short_of_the_end_does_not():
    server, _ = control(subject_state={'y': 0.0},
                        state_update={'y': protocols.LinearTrack.TRACK_LENGTH - 0.01})
    server.end_trial.assert_not_called()


def test_the_fresh_update_wins_over_the_stale_accumulated_state():
    """The doc's trap: subject_state still holds the PREVIOUS position when the function runs.
    A condition reading it instead of state_update fires one update late -- and if the subject
    crosses the line on the run's last update, never."""
    server, _ = control(subject_state={'y': 0.0},                               # not there yet...
                        state_update={'y': protocols.LinearTrack.TRACK_LENGTH + 0.01})  # ...but is now
    server.end_trial.assert_called_once_with(reason='reached_track_end')


def test_an_update_without_y_falls_back_to_the_accumulated_position():
    """Trackers report only what changed; a pure turn must not read as position zero."""
    server, _ = control(subject_state={'y': protocols.LinearTrack.TRACK_LENGTH + 0.01},
                        state_update={'theta': 15.0})
    server.end_trial.assert_called_once_with(reason='reached_track_end')


def test_the_state_update_is_returned_unchanged():
    """The function must return a state update -- it is the closed-loop path to the screens --
    and this one's only job is ending the trial, so it must pass the update through untouched."""
    update = {'y': 0.05, 'theta': 3.0}
    _, returned = control(subject_state={}, state_update=update)
    assert returned == {'y': 0.05, 'theta': 3.0}


def test_the_stimulus_and_the_finish_line_cannot_disagree():
    """The tower is placed from the same class attribute the server-side condition reads, which
    is the reason TRACK_LENGTH is not a GUI-editable protocol parameter (the server process would
    not see the edit)."""
    protocol = protocols.LinearTrack(cfg={})
    protocol.trial_protocol_parameters = protocol.get_protocol_parameter_defaults()
    protocol.get_trial_parameters()
    tower = next(p for p in protocol.trial_stim_parameters if p['name'] == 'Tower')
    assert tower['cylinder_location'][1] > protocols.LinearTrack.TRACK_LENGTH, \
        'the tower should stand at or past the finish line, not before it'
    assert 'track_length' not in protocol.protocol_parameters


# --- BaseProtocol.voltage_out: one code path for rigs with and without the hardware --------------

def test_voltage_out_targets_the_module_when_the_rig_has_it():
    protocol = protocols.LinearTrack(cfg={})
    protocol.available_modules = ['visual', 'voltage_out']
    manager = mock.MagicMock()

    assert protocol.voltage_out(manager) is manager.target.return_value
    manager.target.assert_called_once_with('voltage_out')


def test_voltage_out_targets_the_module_when_the_server_does_not_advertise():
    """available_modules is None for a server that never said what it has (an older stimpack);
    has_module answers True then, so adopting the helper changes nothing until servers report."""
    protocol = protocols.LinearTrack(cfg={})
    assert protocol.available_modules is None
    manager = mock.MagicMock()

    assert protocol.voltage_out(manager) is manager.target.return_value


def test_voltage_out_drops_calls_on_a_rig_without_the_module():
    protocol = protocols.LinearTrack(cfg={})
    protocol.available_modules = ['visual']          # a laptop: no voltage hardware
    manager = mock.MagicMock()

    sink = protocol.voltage_out(manager)
    sink.setup_pulse_wave_stream_out(output_channel='DAC0', freq=2.0, amp=1.0, pulse_width=0.1)
    sink.send_trigger()                              # any method name: all of them no-op

    manager.target.assert_not_called()               # nothing was sent to be dropped server-side


def test_voltage_out_says_so_once_not_per_call(capsys):
    """The point of the helper over bare target(): a skipped rig says so once per run, instead of
    the server warning on every dropped request."""
    protocol = protocols.LinearTrack(cfg={})
    protocol.available_modules = ['visual']
    capsys.readouterr()                              # discard construction-time prints

    protocol.voltage_out(mock.MagicMock())
    protocol.voltage_out(mock.MagicMock())
    protocol.voltage_out(mock.MagicMock())

    out = capsys.readouterr().out
    assert out.count('no voltage_out module') == 1
