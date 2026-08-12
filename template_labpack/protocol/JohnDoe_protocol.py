#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
An example protocol file defining visual stimulus protocols.
The protocols defined here can be imported in experiment configuration files.
"""

from template_labpack.protocol import base_protocol


class BaseProtocol(base_protocol.BaseProtocol):
    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method

# %% Some simple visual stimulus protocol classes

class DriftingSquareGrating(BaseProtocol):
    """
    Drifting square wave grating, painted on a cylinder
    """
    # No __init__ needed: stimpack's BaseProtocol.__init__ already loads the defaults returned by
    # get_run_parameter_defaults() and get_protocol_parameter_defaults() below. Define __init__
    # only when a protocol has something of its own to set up (see LinearTrack).

    def get_trial_parameters(self):
        super().get_trial_parameters()
        
        center = self.adjust_center(self.trial_protocol_parameters['center'])
        centerX = center[0]
        centerY = center[1]

        self.trial_stim_parameters = {'name': 'RotatingGrating',
                                      'period': self.trial_protocol_parameters['period'],
                                      'rate': self.trial_protocol_parameters['rate'],
                                      'color': [1, 1, 1, 1],
                                      'mean': self.trial_protocol_parameters['mean'],
                                      'contrast': self.trial_protocol_parameters['contrast'],
                                      'angle': self.trial_protocol_parameters['angle'],
                                      'offset': 0.0,
                                      'cylinder_radius': 1,
                                      'cylinder_height': 10,
                                      'profile': 'square',
                                      'theta': centerX,
                                      'phi': centerY}

    def get_protocol_parameter_defaults(self):
        return {'pre_time': 1.0,
                'stim_time': 4.0,
                'tail_time': 1.0,
                
                'period': 20.0,
                'rate': 20.0,
                'contrast': 1.0,
                'mean': 0.5,
                'angle': [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0],
                'center': (0, 0),
                }

    def get_run_parameter_defaults(self):
        return {'num_trials': 40,
                'idle_color': 0.5,
                'all_combinations': True,
                'randomize_order': True}

# %% An audio protocol, playing this labpack's own sound

class AudioSweep(BaseProtocol):
    """
    Play the labpack's FrequencySweep sound (template_labpack/audio/sounds.py).

    Sounds are not protocols, so FrequencySweep itself never appears in the GUI's dropdown: a
    protocol names it in a stimulus descriptor, exactly the way visual protocols name a stimulus
    class, and the descriptor's 'target' is what routes it to the audio module instead of the
    screens. The class reaches the server because module_paths.audio_stim names its directory.

    Runs anywhere: on a machine that cannot play (no sound card, or no stimpack[audio]), the
    server has no audio module and each trial reports a warning instead of pretending to play.
    """

    def get_trial_parameters(self):
        super().get_trial_parameters()

        self.trial_stim_parameters = {'name': 'FrequencySweep',
                                      'target': 'audio',
                                      'duration': self.trial_protocol_parameters['stim_time'],
                                      'f_start': self.trial_protocol_parameters['f_start'],
                                      'f_end': self.trial_protocol_parameters['f_end'],
                                      'volume': self.trial_protocol_parameters['volume']}

    def get_protocol_parameter_defaults(self):
        return {'pre_time': 0.5,
                'stim_time': 2.0,
                'tail_time': 0.5,

                'f_start': 100.0,
                'f_end': [300.0, 900.0],   # a swept dimension: shallow and steep sweeps alternate
                'volume': 0.5}

    def get_run_parameter_defaults(self):
        return {'num_trials': 4,
                'idle_color': 0.5,
                'all_combinations': True,
                'randomize_order': True}

# %%

class MovingEllipsoid(BaseProtocol):
    def get_trial_parameters(self):
        super().get_trial_parameters()

        stim_time = self.trial_protocol_parameters['stim_time']

        x_trajectory = {'name': 'TVPairs',
                        'tv_pairs': [(0, -2), (stim_time, 2)],
                        'kind': 'linear'}
        y_trajectory = {'name': 'TVPairs',
                        'tv_pairs': [(0, 4), (stim_time, 6)],
                        'kind': 'linear'}
        z_trajectory = {'name': 'TVPairs',
                        'tv_pairs': [(0, -2), (stim_time, 2)],
                        'kind': 'linear'}

        yaw_trajectory = {'name': 'TVPairs',
                            'tv_pairs': [(0, 0), (stim_time, 90*stim_time)],
                            'kind': 'linear'}
        pitch_trajectory   = {'name': 'TVPairs',
                            'tv_pairs': [(0, 0), (stim_time, 90*stim_time)],
                            'kind': 'linear'}
        roll_trajectory = {'name': 'TVPairs',
                            'tv_pairs': [(0, 0), (stim_time, 0)],
                            'kind': 'linear'}

        self.trial_stim_parameters = {'name': 'MovingEllipsoid',
                            'x_length': self.trial_protocol_parameters['dimensions'][0],
                            'y_length': self.trial_protocol_parameters['dimensions'][1],
                            'z_length': self.trial_protocol_parameters['dimensions'][2],
                            'x': x_trajectory,
                            'y': y_trajectory,
                            'z': z_trajectory,
                            'yaw': yaw_trajectory,
                            'pitch': pitch_trajectory,
                            'roll': roll_trajectory,
                            'n_subdivisions': 6}

    def get_protocol_parameter_defaults(self):
        return {'pre_time': 0.5,
                'stim_time': 4.0,
                'tail_time': 0.5,

                'dimensions': (2,1,1),
                }

    def get_run_parameter_defaults(self):
        return {'num_trials': 2,
                'idle_color': 0.5,
                'all_combinations': True,
                'randomize_order': True}

# %% A trial that ends on behavior rather than on the clock

class LinearTrack(BaseProtocol):
    """
    A virtual linear track: the trial ends when the subject reaches the end of it.

    The subject starts each trial at the origin (BaseProtocol.start_stimuli zeroes the tracker
    position as the stimulus starts) and walks forward, over a textured floor and toward a tower
    marking the far end. Crossing TRACK_LENGTH ends the trial early; a subject that never gets
    there is timed out by stim_time as usual.

    The condition cannot be checked in this class's own methods: they run on the CLIENT, which
    never sees subject state and cannot ask for it (requests carry no reply). So the check lives
    in server_side_state_dependent_control below, which stimpack calls on the SERVER on every
    tracker update. Full story: stimpack's docs, "Trials that end when the animal does something".

    To try it without hardware: run on a rig config with loco_available: True (the example server
    uses KeyTrac, a keyboard stand-in tracker), check do_loco in the GUI's run parameters, and
    walk forward by holding W in the KeyTrac window -- the trial ends as you arrive at the tower.
    """

    # The length of the track, in meters -- deliberately a class attribute, not a protocol
    # parameter. server_side_state_dependent_control runs in the server process, which imports
    # this module and reads the *class*; it never sees the protocol object, so a value edited in
    # the GUI would move the tower (below) without moving the finish line. Keeping the number
    # here means the stimulus and the trial-ending condition cannot disagree.
    TRACK_LENGTH = 0.15  # 15 presses of W at KeyTrac's default 0.01 m step

    def __init__(self, cfg):
        super().__init__(cfg)
        # Ask stimpack to load server_side_state_dependent_control onto the server for the
        # duration of the run. Without this flag the function below is never called.
        self.use_server_side_state_dependent_control = True

    @staticmethod
    def server_side_state_dependent_control(server, subject_state, state_update):
        """Runs ON THE SERVER, once per tracker update. Must return a state_update; modifying it
        is the closed-loop part (a gain, an offset) -- ending the trial is an extra thing it may
        do along the way. This one leaves the update untouched.
        """
        # Read the fresh value from state_update first, and only fall back to subject_state.
        # state_update holds what the tracker just reported (only the keys that changed);
        # subject_state is the accumulated state as it was BEFORE this update. A condition
        # written against subject_state alone therefore fires one update late -- and if the
        # subject crosses the line on the run's last update, never.
        y = state_update.get('y', subject_state.get('y', 0))
        if y > LinearTrack.TRACK_LENGTH:
            # Ends only the trial in progress, as if its timer had elapsed; the run goes on to
            # the next trial. The reason is recorded with the trial (trial_end_reason), which is
            # what lets analysis tell "reached the end in 1.4 s" from "timed out at 30 s".
            server.end_trial(reason='reached_track_end')
        # (Any per-trial state you keep on `server` needs a leading underscore -- the server
        # turns unknown bare attribute names into remote calls. See the docs page above.)
        return state_update

    def get_trial_parameters(self):
        super().get_trial_parameters()

        # Both stimuli are world-fixed. With closed-loop locomotion the viewpoint follows the
        # subject, so walking forward (+y) carries it over the floor and toward the tower.
        floor = {'name': 'TexturedGround',   # random texture -> optic flow while walking
                 'color': [0.5, 0.5, 0.5, 1.0],
                 'z_level': -0.05,
                 'rand_seed': 0}
        goal = {'name': 'Tower',             # the landmark at the end of the track
                'color': [1, 0, 0, 1],
                'cylinder_radius': 0.02,
                'cylinder_height': 0.10,
                # Just past the finish line, so the trial ends as the subject reaches it rather
                # than after walking through it.
                'cylinder_location': [0, self.TRACK_LENGTH + 0.05, 0]}
        self.trial_stim_parameters = [floor, goal]

    def get_protocol_parameter_defaults(self):
        # stim_time is a ceiling here, not the expected duration: behavior usually ends the trial
        # first. The data file records what actually happened, per trial: trial_duration,
        # ended_early, and trial_end_reason.
        return {'pre_time': 0.5,
                'stim_time': 30.0,
                'tail_time': 0.5,
                'loco_pos_closed_loop': 1,   # couple position to the tracker during stim_time
                }

    def get_run_parameter_defaults(self):
        return {'num_trials': 5,
                'idle_color': 0.5,
                'all_combinations': True,
                'randomize_order': False}

# %%