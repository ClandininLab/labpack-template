"""Custom sounds, loaded on the server's audio module when the config names this directory.

Subclass BaseSound and the class resolves by name from a protocol's stimulus descriptor
(``{'name': 'FrequencySweep', 'target': 'audio', ...}``) -- no registration step, the same way
custom visual stimuli resolve. Parameters are plain numbers rather than trajectories because the
whole waveform is generated once at trial load; nothing written here runs on the real-time audio
thread.
"""
import numpy as np

from stimpack.audio.sounds import BaseSound


class FrequencySweep(BaseSound):
    """A linear sweep from f_start to f_end: the worked example from stimpack's audio docs.

    :param duration: seconds
    :param f_start: Hz at the first sample
    :param f_end: Hz at the last
    :param volume: peak amplitude, 0 to 1
    """

    def __init__(self, duration=1.0, f_start=100.0, f_end=900.0, volume=0.5):
        self.duration, self.f_start, self.f_end, self.volume = duration, f_start, f_end, volume

    def generate(self, sample_rate):
        t = np.linspace(0, self.duration, round(self.duration * sample_rate), endpoint=False)
        rate = (self.f_end - self.f_start) / self.duration
        phase = 2 * np.pi * (self.f_start * t + 0.5 * rate * t ** 2)
        return self.volume * np.sin(phase)
