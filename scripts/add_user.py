#!/usr/bin/env python3
"""Add a person to this labpack: their config, protocol module and presets directory.

    python scripts/add_user.py tc --name "Tim Currier" --dry-run
    python scripts/add_user.py tc --name "Tim Currier"

creates

    configs/tc_config.yaml               from configs/example_config.yaml, with experimenter,
                                         parameter_presets_dir and module_paths.protocol filled in
    <package>/protocol/tc_protocol.py    from the template's JohnDoe_protocol.py (working examples
                                         to edit or delete); --empty gives a skeleton instead
    presets/tc/                          where the GUI's "Save preset" will write

Run once per person, after scripts/rename_package.py. Nothing existing is overwritten.

The id is short and lower case by convention (initials are typical): it names the files, and
`--name` is what goes in the `experimenter` field written into every data file.
"""
import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rename_package import find_current_package  # noqa: E402

TEMPLATE_CONFIG = os.path.join('configs', 'example_config.yaml')
TEMPLATE_PROTOCOL = 'JohnDoe_protocol.py'
TEMPLATE_USER = 'JohnDoe'
TEMPLATE_PRESETS = 'presets/johndoe'
# Spelled in two halves so scripts/rename_package.py, which rewrites the package name across the repo,
# leaves this check meaning what it says.
TEMPLATE_PACKAGE = 'template' + '_labpack'

SKELETON = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protocols for {name}.

Every BaseProtocol subclass in this module appears in the GUI's Protocol dropdown, with one field
per key in get_protocol_parameter_defaults(). Wired in by configs/{user}_config.yaml.
"""
from {package}.protocol import base_protocol


class BaseProtocol(base_protocol.BaseProtocol):
    def __init__(self, cfg):
        super().__init__(cfg)


class Flash(BaseProtocol):
    """A full-field flash: a starting point to copy."""

    def get_trial_parameters(self):
        super().get_trial_parameters()
        self.trial_stim_parameters = {{'name': 'ConstantBackground',
                                      'color': self.trial_protocol_parameters['intensity']}}

    def get_protocol_parameter_defaults(self):
        return {{'pre_time': 1.0,
                'stim_time': 0.5,
                'tail_time': 1.0,
                'intensity': [0.0, 1.0]}}

    def get_run_parameter_defaults(self):
        return {{'num_trials': 10,
                'idle_color': 0.5,
                'all_combinations': True,
                'randomize_order': True}}
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('user', help="short id for file names, e.g. initials: tc")
    parser.add_argument('--name', help="experimenter name written into data files "
                                       "(default: the id)")
    parser.add_argument('--empty', action='store_true',
                        help="start the protocol module from a one-protocol skeleton instead of "
                             "the template's examples")
    parser.add_argument('--dry-run', action='store_true',
                        help="show what would be created without writing anything")
    parser.add_argument('--root', default=REPO_ROOT,
                        help="labpack directory (default: the repo this script lives in)")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    user = args.user
    name = args.name or user
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', user):
        sys.exit(f"'{user}' can't name files and modules: use letters, digits and underscores, "
                 f"starting with a letter.")
    if '\n' in name or '"' in name:
        sys.exit("--name can't contain quotes or line breaks.")

    package = find_current_package(root)
    if package == TEMPLATE_PACKAGE:
        print(f"Note: the package is still '{TEMPLATE_PACKAGE}'. Run scripts/rename_package.py "
              "first, so the paths written here don't need changing later.\n")

    config_src = os.path.join(root, TEMPLATE_CONFIG)
    protocol_dir = os.path.join(root, package, 'protocol')
    protocol_src = os.path.join(protocol_dir, TEMPLATE_PROTOCOL)

    config_dst = os.path.join(root, 'configs', f'{user}_config.yaml')
    protocol_dst = os.path.join(protocol_dir, f'{user}_protocol.py')
    presets_dst = os.path.join(root, 'presets', user)

    for path in (config_dst, protocol_dst):
        if os.path.exists(path):
            sys.exit(f"{os.path.relpath(path, root)} already exists. Nothing written.")
    if not os.path.exists(config_src):
        sys.exit(f"Template config {TEMPLATE_CONFIG} not found; can't derive a config from it.")
    if not args.empty and not os.path.exists(protocol_src):
        sys.exit(f"{os.path.relpath(protocol_src, root)} not found. Use --empty for a skeleton.")

    # --- config: the template's, with the three per-person fields filled in --------------------
    with open(config_src, encoding='utf-8') as f:
        config = f.read()
    replacements = [
        (rf'^experimenter:\s*{TEMPLATE_USER}\b.*$', f'experimenter: "{name}"'),
        (rf'{re.escape(package)}/protocol/{re.escape(TEMPLATE_PROTOCOL)}',
         f'{package}/protocol/{user}_protocol.py'),
        (rf'(parameter_presets_dir:\s*){re.escape(TEMPLATE_PRESETS)}\b', rf'\g<1>presets/{user}'),
    ]
    for pattern, repl in replacements:
        config, n = re.subn(pattern, repl, config, flags=re.MULTILINE)
        if n == 0:
            sys.exit(f"Couldn't find {pattern!r} in {TEMPLATE_CONFIG}; has it been edited? "
                     f"Nothing written.")

    # --- protocol module ------------------------------------------------------------------------
    if args.empty:
        protocol = SKELETON.format(name=name, user=user, package=package)
    else:
        with open(protocol_src, encoding='utf-8') as f:
            protocol = f.read()
        protocol = protocol.replace(
            '"""\nAn example protocol file defining visual stimulus protocols.',
            f'"""\nProtocols for {name}, started from the template\'s examples: edit or delete them.',
            1)

    rel = lambda p: os.path.relpath(p, root)  # noqa: E731
    print(f"Adding '{user}' ({name}) to {package}:")
    print(f"  {rel(config_dst)}      (from {TEMPLATE_CONFIG})")
    print(f"  {rel(protocol_dst)}  "
          + ("(skeleton)" if args.empty else f"(from {TEMPLATE_PROTOCOL})"))
    print(f"  {rel(presets_dst)}/")
    if args.dry_run:
        print("\nDry run. Nothing written.")
        return

    with open(config_dst, 'w', encoding='utf-8') as f:
        f.write(config)
    with open(protocol_dst, 'w', encoding='utf-8') as f:
        f.write(protocol)
    os.makedirs(presets_dst, exist_ok=True)
    open(os.path.join(presets_dst, '.gitkeep'), 'a').close()

    print(f"\nDone. Edit {rel(config_dst)} for this person's rigs (data_directory, server address),")
    print("then pick it in stimpack's startup dialog. Check:  stimpack --check-labpack")


if __name__ == '__main__':
    main()
