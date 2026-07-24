# Labpack

A template for your lab-specific [Stimpack](https://github.com/ClandininLab/stimpack) configuration:
rig configs, protocols, custom stimuli, and device drivers.

[Stimpack documentation and quick start](https://stimpack.readthedocs.io/en/latest/)

Stimpack itself ships no lab-specific configuration. You clone this repo, rename/edit the pieces
below, and point stimpack at it — stimpack then loads your modules dynamically at runtime.

## Getting started

1. Clone this repo and install it (Python >= 3.10; `stimpack` is installed as a dependency):
   ```
   git clone https://github.com/ClandininLab/labpack   # then rename it for your lab
   cd labpack
   pip install -e .
   ```
   Add hardware drivers only if the rig needs them: `pip install -e .[nidaq]` or `.[labjack]`.

2. Launch the GUI (`stimpack`) and use **Labpack Dir** in the startup dialog to point at this
   directory. The choice is remembered in `path_to_labpack.txt` in stimpack's user config dir.

3. Copy `configs/example_config.yaml` to `configs/<yourlab>_config.yaml` and edit it. It appears in
   the startup dialog's config dropdown.

## What's here

| Path | What it is / what to edit |
|---|---|
| `configs/*.yaml` | Rig configs: experimenter, subject metadata fields, per-rig settings, and `module_paths`. **Start here.** |
| `labpack/protocol/base_protocol.py` | Lab-wide protocol base. Put helpers shared by all your protocols here. |
| `labpack/protocol/JohnDoe_protocol.py` | Example protocols. Rename to `<you>_protocol.py` and write your own; every `BaseProtocol` subclass appears in the GUI dropdown. |
| `labpack/visual_stim/example/` | Custom stimuli, shapes, trajectories and distributions. These are exec'd **on the server**; subclasses of stimpack's `BaseProgram` / `Trajectory` / `Distribution` become usable by name. |
| `labpack/device/daq.py` | DAQ drivers (NI, LabJack) and the `DAQonServer` proxy used when the DAQ lives on the rig machine. Referenced by the `trigger:` string in a rig config. |
| `labpack/device/locomotion/` | Locomotion managers (e.g. FicTrac). Subclass stimpack's `LocoClosedLoopManager` and implement `_parse_line`. |
| `labpack/client.py`, `labpack/data.py` | Empty passthroughs over stimpack's `BaseClient` / `BaseData` — override here if you need custom client behavior or a different data layout. |
| `server/example_server.py` | Example rig server: screen geometry, locomotion, DAQ. Copy one per rig. |
| `server/base_server.py` | Lab-wide server base; forwards everything to stimpack's `BaseServer`. |

## Notes

- **Custom stimuli must be listed under `module_paths.visual_stim`** in your config. An older layout
  used `server_options.visual_stim_module_paths`; current stimpack does not read that key, so
  stimuli listed there are never loaded and referencing them fails with "0 stimulus candidates".
- **Protocols reference stimuli by class name**, not by import, e.g.
  `self.epoch_stim_parameters = {'name': 'MovingPatch', ...}`. The name is resolved on the server
  against every loaded `BaseProgram` subclass — so a stimulus is available as soon as its module is
  loaded, with no registration step.
- **Binding**: stimpack's server binds loopback (`127.0.0.1`) by default, because the RPC control
  channel is unauthenticated. For a remote client, set the rig's address explicitly in that rig's
  server script and firewall the port to the trusted rig network.
- **One protocol, several rigs.** The server tells the client which modules it has, so a protocol
  can adapt instead of assuming the hardware:

  ```python
  if self.has_module('voltage_out') and self.epoch_protocol_parameters['opto_amp'] > 0:
      multicall.target('voltage_out').setup_pulse_wave_stream_out(
          channels_config={'name': self.opto['channel'], 'high': amp, 'low': 0.0}, ...)
  ```

  `voltage_out` is the module for anything driven by an output voltage — optogenetics, odor, reward,
  shock. (`target('daq')` still works and maps to it, with a one-time deprecation warning.)
  `has_module()` returns True when the server hasn't advertised, so adopting it changes nothing
  until the server reports. What is *wired* to that voltage — an LED, a valve, on which channel — is
  lab-specific: keep it in your own `rig_config` keys, as with the commented‑out `opto:` example.
