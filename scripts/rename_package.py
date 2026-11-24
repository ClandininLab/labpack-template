#!/usr/bin/env python3
"""Name this labpack for your lab: the Python package and the lab's stimulus directory.

The template ships its package as `template_labpack` and its stimuli in `visual_stim/example/`, so it
can be installed alongside a lab's existing labpack. Renaming both is the first thing to do with a
new copy:

    python scripts/rename_package.py smith --dry-run   # show what would change
    python scripts/rename_package.py smith             # template_labpack -> smith_labpack
                                                       # visual_stim/example -> visual_stim/smith

The name you give is the lab's short name. The package becomes `<name>_labpack` unless the name
already ends in `_labpack` or `_pack` (so `smithlab_pack` stays `smithlab_pack`), and the stimulus
directory takes the short name. Either can be set explicitly with --package / --stim-dir.

People are added separately, once each, with scripts/add_user.py: a labpack belongs to a lab, while
configs, protocol files and presets belong to the people in it.

Why the stimulus directory is renamed here too: stimpack loads `stimuli.py` by file path, but the
helpers it imports (shapes, utilities) are imported by package path, e.g.
`from smith_labpack.visual_stim.smith.shapes import ...`. The directory name is therefore baked
into code, and renaming it by hand silently breaks the import -- the server then loads none of the
lab's stimuli. This script moves the directory and rewrites every reference to it together.

What has to agree, and is changed together:

  1. the package directory name               (on disk)
  2. `name` and `packages` in setup.py        (at install time)
  3. `from <pkg>...` imports                  (when a protocol or stimulus module is imported)
  4. `module_paths` in every config           (when stimpack loads your modules)
  5. the stimulus directory and its imports   (when the server execs stimuli.py)

Miss #4 or #5 and stimpack reports "0 stimulus candidates" at run time. Afterwards,
`stimpack --check-labpack --deep` loads each visual_stim directory and reports one that fails.
"""
import argparse
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Suffixes worth rewriting. Everything else (images, .pyc, resources) is left alone.
TEXT_SUFFIXES = ('.py', '.yaml', '.yml', '.md', '.rst', '.txt', '.cfg', '.toml')

SKIP_DIRS = {'.git', '__pycache__', '.pytest_cache', 'build', 'dist', '.eggs', '.venv', 'venv'}

PACKAGE_SUFFIXES = ('_labpack', '_pack')


def find_current_package(root):
    """The package directory: a top-level dir with an __init__.py, excluding support directories."""
    candidates = [
        name for name in sorted(os.listdir(root))
        if name not in SKIP_DIRS
        and not name.endswith('.egg-info')
        and os.path.isdir(os.path.join(root, name))
        and os.path.exists(os.path.join(root, name, '__init__.py'))
    ]
    if not candidates:
        sys.exit(f"No Python package found in {root} (looked for a top-level directory with an "
                 f"__init__.py). Are you running this from inside your labpack?")
    if len(candidates) > 1:
        sys.exit(f"Found more than one candidate package in {root}: {candidates}. "
                 f"Rename by hand, or remove the ones that are not your labpack.")
    return candidates[0]


def find_stim_dirs(root, package):
    """Directories under <package>/visual_stim/ that hold a stimuli.py."""
    base = os.path.join(root, package, 'visual_stim')
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base)
                  if os.path.isfile(os.path.join(base, d, 'stimuli.py')))


def is_valid_identifier(name):
    return re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) is not None


def resolve_names(name, package=None, stim_dir=None):
    """(package, stim_dir) from the short name and any explicit overrides."""
    if package is None:
        package = name if name.endswith(PACKAGE_SUFFIXES) else f'{name}_labpack'
    if stim_dir is None:
        stim_dir = name
        for suffix in PACKAGE_SUFFIXES:
            if stim_dir.endswith(suffix) and len(stim_dir) > len(suffix):
                stim_dir = stim_dir[:-len(suffix)]
                break
    return package, stim_dir


def text_files(root):
    # This file talks *about* the template's names, so rewriting it would turn its own explanation
    # into nonsense. Other scripts in the labpack are rewritten normally.
    myself = os.path.abspath(__file__)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith('.egg-info')]
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if filename.endswith(TEXT_SUFFIXES) and os.path.abspath(path) != myself:
                yield path


def identifier(name):
    """`name` as a whole identifier: not part of a longer one on either side."""
    # \b would not stop `template_labpack` matching inside `my_template_labpack`, because _ is a
    # word character on both sides. Require a non-identifier character (or a boundary) instead.
    return rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])'


def rewrite_text(text, old_pkg, new_pkg, old_stim, new_stim):
    if old_pkg != new_pkg:
        text = re.sub(identifier(old_pkg), new_pkg, text)
    if old_stim and new_stim and old_stim != new_stim:
        # Only as a path or module segment directly under visual_stim, so a word like "example"
        # elsewhere in a comment or docstring is left alone.
        text = re.sub(rf'(visual_stim[./]){re.escape(old_stim)}(?![A-Za-z0-9_])',
                      rf'\g<1>{new_stim}', text)
    return text


def git_mv(root, src, dst):
    """git mv when the labpack is a git checkout (so history shows a move); plain rename otherwise."""
    if os.path.isdir(os.path.join(root, '.git')):
        if subprocess.run(['git', '-C', root, 'mv', src, dst], capture_output=True).returncode == 0:
            return
    os.rename(os.path.join(root, src), os.path.join(root, dst))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('name', help="the lab's short name, e.g. smith (-> smith_labpack, "
                                     "visual_stim/smith)")
    parser.add_argument('--package', help="package name, if not <name>_labpack")
    parser.add_argument('--stim-dir', help="stimulus directory name, if not <name>")
    parser.add_argument('--keep-stim-dir', action='store_true',
                        help="rename the package only; leave the stimulus directory as it is")
    parser.add_argument('--dry-run', action='store_true',
                        help="show what would change without writing anything")
    parser.add_argument('--root', default=REPO_ROOT,
                        help="labpack directory (default: the repo this script lives in)")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    new_pkg, new_stim = resolve_names(args.name, args.package, args.stim_dir)

    for label, value in (('package', new_pkg), ('stimulus directory', new_stim)):
        if '-' in value:
            sys.exit(f"'{value}' contains a hyphen. Python names use underscores "
                     f"(the *repository* may use hyphens; they need not match).")
        if not is_valid_identifier(value):
            sys.exit(f"'{value}' is not a valid {label} name: use letters, digits and "
                     f"underscores, and do not start with a digit.")

    old_pkg = find_current_package(root)

    old_stim = None
    if not args.keep_stim_dir:
        stim_dirs = find_stim_dirs(root, old_pkg)
        if len(stim_dirs) == 1:
            old_stim = stim_dirs[0]
        elif len(stim_dirs) > 1:
            print(f"Found several stimulus directories ({', '.join(stim_dirs)}); leaving them as "
                  f"they are. Rename one with --stim-dir after moving the others aside, or by hand.")
    if old_stim == new_stim:
        old_stim = None

    if old_pkg == new_pkg and old_stim is None:
        sys.exit(f"The package is already '{new_pkg}'"
                 + ("" if args.keep_stim_dir else f" and its stimulus directory '{new_stim}'")
                 + ". Nothing to do.")

    print(f"Package:             {old_pkg} -> {new_pkg}" if old_pkg != new_pkg
          else f"Package:             {old_pkg} (unchanged)")
    if old_stim:
        print(f"Stimulus directory:  visual_stim/{old_stim} -> visual_stim/{new_stim}")
    print(f"  in {root}\n")

    # --- 1. content, across every text file -----------------------------------------------------
    edits = []
    for path in sorted(text_files(root)):
        try:
            with open(path, encoding='utf-8') as f:
                original = f.read()
        except UnicodeDecodeError:
            continue
        updated = rewrite_text(original, old_pkg, new_pkg, old_stim, new_stim)
        if updated != original:
            changes = [(i + 1, a, b) for i, (a, b)
                       in enumerate(zip(original.split('\n'), updated.split('\n'))) if a != b]
            edits.append((path, changes, updated))

    for path, changes, _ in edits:
        rel = os.path.relpath(path, root)
        print(f"  {rel}  ({len(changes)} line{'s' if len(changes) != 1 else ''})")
        for lineno, before, after in changes[:3]:
            print(f"      {lineno}: - {before.strip()}")
            print(f"      {lineno}: + {after.strip()}")
        if len(changes) > 3:
            print(f"      ... and {len(changes) - 3} more")

    # --- 2. the directories ---------------------------------------------------------------------
    moves = []
    if old_pkg != new_pkg:
        moves.append((old_pkg, new_pkg))
    if old_stim:
        moves.append((os.path.join(new_pkg, 'visual_stim', old_stim),
                      os.path.join(new_pkg, 'visual_stim', new_stim)))
    print()
    for src, dst in moves:
        print(f"  {src}/ -> {dst}/   (directory)")

    if args.dry_run:
        total = sum(len(c) for _, c, _ in edits)
        print(f"\nDry run: {total} line(s) across {len(edits)} file(s), plus {len(moves)} "
              f"director{'y' if len(moves) == 1 else 'ies'}. Nothing written.")
        return

    for src, dst in moves:
        if os.path.exists(os.path.join(root, dst)):
            sys.exit(f"\n{os.path.join(root, dst)} already exists. Move it aside first.")

    for path, _, updated in edits:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated)
    for src, dst in moves:
        git_mv(root, src, dst)

    print("\nDone. Now:")
    if old_pkg != new_pkg:
        print(f"  pip uninstall {old_pkg}".ljust(42) + "# if it was installed under the old name")
    print("  pip install -e .".ljust(42) + "# (re)install under the new name")
    print("  python scripts/add_user.py <initials>".ljust(42) + "# a config, protocol file and "
                                                                "presets for each person")
    print("\nThen check it over:  stimpack --check-labpack --deep")


if __name__ == '__main__':
    main()
