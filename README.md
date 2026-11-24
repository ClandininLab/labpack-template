<img src="https://raw.githubusercontent.com/ClandininLab/stimpack/main/stimpack/_assets/labpack_icon.svg" align="left" width="90" alt="labpack: two display screens angled around a subject, in labpack yellow"/>

# labpack-template

A template for your lab-specific [Stimpack](https://github.com/ClandininLab/stimpack) configuration:
rig configs, protocols, custom stimuli, and device drivers.

<br clear="left"/>

[Stimpack documentation and quick start](https://stimpack.readthedocs.io/en/latest/)

Worth reading before writing protocols, since they cover the things a labpack gets wrong quietly:
[modules and targeting](https://stimpack.readthedocs.io/en/latest/modules_and_targets.html) (an
untargeted call goes to the server's root node, not to every module),
[checking a labpack](https://stimpack.readthedocs.io/en/latest/check_labpack.html), and
[how a run ended](https://stimpack.readthedocs.io/en/latest/run_outcomes.html).

Stimpack itself ships no lab-specific configuration. You make your own copy of this repo, rename
and edit the pieces below, and point stimpack at it — stimpack then loads your modules dynamically
at runtime.

## Getting started

1. Press **Use this template** at the top of this page to create your lab's own repository, then
   clone it. (You can make it **private** — rig configs, data paths and experimenter names usually
   should be. A *fork* of a public repo cannot be private; a template copy can.)

   ```
   git clone https://github.com/<your-org>/<your-labpack>
   cd <your-labpack>
   ```

   Staying a git checkout pays off directly: stimpack stamps the labpack's current commit into
   every data file it records (with a `.dirty` marker when the tree has uncommitted changes), so
   committing before recording is what makes an experiment answerable a year later.

2. Name the labpack for your lab, then install it (Python >= 3.10; `stimpack` comes as a
   dependency):
   ```
   python scripts/rename_package.py smith   # --dry-run first, to see what it will touch
   pip install -e .
   ```
   That makes the package `smith_labpack` and the lab's stimulus directory `visual_stim/smith`
   (`--package` and `--stim-dir` choose other names). Add hardware drivers only if the rig needs
   them: `pip install -e .[nidaq]` or `.[labjack]`.

   The template's names are generic so it can be installed side by side with an existing labpack.
   Renaming means yours can be too, and that a traceback says whose code it is in. The script
   changes everything that has to agree, together: the package directory, `name`/`packages` in
   `setup.py`, the package imports, the `module_paths` entries in every config, and the stimulus
   directory with the imports inside it. That last one matters: `stimuli.py` is loaded by file
   path, but the helpers it imports are imported by package path, so renaming that directory by
   hand leaves a stale import and the server loads none of your stimuli.

   Stimpack never imports your labpack by name. It resolves the directory recorded in
   `path_to_labpack.txt` and loads your modules by file path, so the name is yours to choose.

3. Add each person who will run experiments, once:
   ```
   python scripts/add_user.py jd --name "Jane Doe"
   ```
   creates `configs/jd_config.yaml` (experimenter, presets directory and protocol module filled
   in), `<package>/protocol/jd_protocol.py` (the template's example protocols, to edit; `--empty`
   for a skeleton) and `presets/jd/`. A labpack belongs to the lab; configs, protocols and presets
   belong to people, which is why this is a separate step.

4. Launch the GUI (`stimpack`), use **Labpack Dir** in the startup dialog to point at this
   directory, and pick your config. The directory is remembered in `path_to_labpack.txt` in
   stimpack's user config dir. Then edit your config's `rig_config` for your rigs.

5. Check it: `stimpack --check-labpack --deep`.

## Tests

```shell
pip install -e .[test]
pytest
```

A labpack holds the rig-specific code, so it holds the rig-specific mistakes, and those are the ones
that cost an experiment. More is testable without hardware than it looks: `tests/` ships with a
worked example that checks the projector's pattern LUT against TI's documentation without a
projector. See `tests/README.md`.

GitHub Actions runs them on 3.10 to 3.12 (`.github/workflows/test.yml`).

### Keeping up with the template

A template copy shares no git history with this repo, so there is no `git pull` from it. When
stimpack changes how labpacks talk to it, the way to find out is to run stimpack's labpack check
against your copy rather than to diff against the template:

```
stimpack --check-labpack        # validates this labpack against the installed stimpack
```

## What's here

| Path | What it is / what to edit |
|---|---|
| `configs/*.yaml` | Rig configs: experimenter, subject metadata fields, per-rig settings, and `module_paths`. **Start here.** |
| `presets/johndoe/` | Saved parameter presets, one YAML file per protocol — the GUI's **Save preset** writes here, and a worked example ships in `DriftingSquareGrating.yaml`. Ensembles — ordered queues of (protocol, preset) pairs the GUI runs back to back — are saved as `.spens` files, plain YAML lists of those pairs, and reference presets by name. |
| `template_labpack/protocol/base_protocol.py` | Lab-wide protocol base. Put helpers shared by all your protocols here. |
| `template_labpack/protocol/JohnDoe_protocol.py` | Example protocols. `scripts/add_user.py` copies them to `<you>_protocol.py` for each person; every `BaseProtocol` subclass appears in the GUI dropdown. |
| `template_labpack/visual_stim/example/` | Custom stimuli, shapes, trajectories and distributions. These are exec'd **on the server**; subclasses of stimpack's `BaseProgram` / `Trajectory` / `Distribution` become usable by name. |
| `template_labpack/audio/` | Custom sound classes, sent to the server's audio module via `module_paths.audio_stim`. Subclasses of stimpack's `BaseSound` become usable by name from a stimulus descriptor with `target: 'audio'`. |
| `template_labpack/daq/` | DAQ drivers (NI, LabJack) and the `DAQonServer` proxy used when the DAQ lives on the rig machine. Referenced by the `trigger:` string in a rig config. |
| `template_labpack/device/dlpc350.py` | TI DLPC350 projectors (LightCrafter 4500 and the optical engines built on it). Sets pattern mode, LED currents, and can display the three color channels of a frame as successive patterns — a 120 Hz link driving the DMD at 360 Hz. |
| `template_labpack/locomotion/` | Locomotion managers (e.g. FicTrac). Subclass stimpack's `LocoClosedLoopManager` and implement `_parse_line`. |
| `template_labpack/client.py`, `template_labpack/data.py` | Empty passthroughs over stimpack's `BaseClient` / `BaseData` — override here if you need custom client behavior or a different data layout. |
| `server/example_server.py` | Example rig server: screen geometry, locomotion, DAQ, audio. Copy one per rig. |
| `server/base_server.py` | Lab-wide server base; forwards everything to stimpack's `BaseServer`. |
| `scripts/` | `rename_package.py` names the labpack for your lab (run once); `add_user.py` adds a person's config, protocol module and presets (run per person). |
| `tests/` | Your tests. Hardware drivers can be stubbed and the bytes they would send checked against the manufacturer's documentation, with no rig attached — see `tests/README.md`. |

## Notes

- **Custom stimuli must be listed under `module_paths.visual_stim`** in your config. An older layout
  used `server_options.visual_stim_module_paths`; current stimpack does not read that key, so
  stimuli listed there are never loaded and referencing them fails with "0 stimulus candidates".
- **Protocols reference stimuli by class name**, not by import, e.g.
  `self.trial_stim_parameters = {'name': 'MovingPatch', ...}`. The name is resolved on the server
  against every loaded `BaseProgram` subclass — so a stimulus is available as soon as its module is
  loaded, with no registration step.
- **Binding**: stimpack's server binds loopback (`127.0.0.1`) by default, because the RPC control
  channel is unauthenticated. For a remote client, set the rig's address explicitly in that rig's
  server script and firewall the port to the trusted rig network.
- **One protocol, several rigs.** The server tells the client which modules it has, so a protocol
  can adapt instead of assuming the hardware:

  ```python
  amp = self.trial_protocol_parameters['opto_amp']
  if amp > 0:
      self.voltage_out(multicall).setup_pulse_wave_stream_out(
          output_channel=self.opto['channel'], freq=2.0, amp=amp, pulse_width=0.1)
  ```

  `voltage_out` is the module for anything driven by an output voltage — optogenetics, odor, reward,
  shock. (`target('daq')` still works and maps to it, with a one-time deprecation warning.)
  `self.voltage_out(...)` is a helper in `base_protocol.py`: on a rig that has the module it is
  just `target('voltage_out')`, and on one that does not it returns a stand-in that drops the
  calls — saying so once per run instead of warning on every request. It decides using
  `has_module()`, which returns True when the server hasn't advertised its modules, so adopting it
  changes nothing until the server reports. What is *wired* to that voltage — an LED, a valve, on
  which channel — is lab-specific: keep it in your own `rig_config` keys, as with the
  commented‑out `opto:` example.
