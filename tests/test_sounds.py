"""The labpack's sound classes, checked without a sound card.

A sound is a pure function of (parameters, sample_rate) -- a BaseSound subclass generating its
whole waveform at trial load -- so everything about it is testable on any machine. What CI pins
here is the labpack-side contract: the class subclasses BaseSound (which is what lets the audio
module resolve it by name), and the waveform matches what its parameters describe.
"""
import numpy as np
import pytest

from stimpack.audio.sounds import BaseSound

from template_labpack.audio.sounds import FrequencySweep


def test_frequency_sweep_is_resolvable_by_the_audio_module():
    """Name resolution walks BaseSound's subclasses; being one is the whole registration step."""
    assert issubclass(FrequencySweep, BaseSound)


def test_frequency_sweep_generates_the_requested_duration():
    assert len(FrequencySweep(duration=0.5).generate(8000)) == 4000


def test_frequency_sweep_respects_volume():
    samples = FrequencySweep(duration=0.25, volume=0.5).generate(8000)
    assert np.max(np.abs(samples)) <= 0.5 + 1e-12


def test_frequency_sweep_actually_sweeps():
    """Mean frequency over the first and last tenth, estimated from zero crossings: a 100->900 Hz
    linear sweep averages 140 Hz over its first tenth and 860 over its last. Catching the classic
    sweep bug -- phase computed from the instantaneous frequency instead of its integral, which
    doubles the sweep rate -- needs the estimate to be no looser than ~10%."""
    rate = 44100
    samples = FrequencySweep(duration=1.0, f_start=100.0, f_end=900.0, volume=1.0).generate(rate)

    def mean_freq(segment):
        crossings = int(np.sum(np.diff(np.signbit(segment))))
        return crossings / 2 / (len(segment) / rate)

    tenth = len(samples) // 10
    assert mean_freq(samples[:tenth]) == pytest.approx(140, rel=0.10)
    assert mean_freq(samples[-tenth:]) == pytest.approx(860, rel=0.05)
