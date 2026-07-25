#!/usr/bin/env python3
"""Rename this labpack's Python package.

The template ships its package as `template_labpack` so that it can be installed alongside a lab's
existing labpack. Renaming it to something lab-specific is the first thing you should do with a new
copy: it means yours can coexist with someone else's too, and that a traceback says whose code it is
in.

Four things have to agree, and they are checked at different moments -- so getting three of four
right fails silently rather than loudly:

  1. the package directory name          (on disk)
  2. `name` and `packages` in setup.py   (at install time)
  3. `from <pkg>...` imports             (when a protocol is imported)
  4. `module_paths` in every config      (when stimpack loads your modules)

Miss #4 and stimpack reports "0 stimulus candidates" at run time, with nothing to point at the
cause. This script does all four together.

Usage:
    python scripts/rename_package.py smithlab_pack --dry-run   # show what would change
    python scripts/rename_package.py smithlab_pack             # do it
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


def is_valid_identifier(name):
    return re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) is not None


def text_files(root):
    # This file talks *about* the template's package name, so rewriting it would turn its own
    # explanation into nonsense ("the template ships its package as smithlab_pack"). Other scripts
    # in the labpack are rewritten normally.
    myself = os.path.abspath(__file__)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith('.egg-info')]
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if filename.endswith(TEXT_SUFFIXES) and os.path.abspath(path) != myself:
                yield path


def rewrite(path, old, new):
    """Replace whole-word occurrences of `old`. Returns the changed lines as (lineno, before, after)."""
    with open(path, encoding='utf-8') as f:
        try:
            original = f.read()
        except UnicodeDecodeError:
            return []

    # \b would not stop `template_labpack` from matching inside `my_template_labpack`, because _ is
    # a word character on both sides. Require a non-identifier character (or a boundary) instead.
    pattern = re.compile(rf'(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])')
    updated = pattern.sub(new, original)
    if updated == original:
        return []

    changes = [(i + 1, a, b)
               for i, (a, b) in enumerate(zip(original.split('\n'), updated.split('\n'))) if a != b]
    return changes, original, updated


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('new_name', help="the new package name, e.g. smithlab_pack")
    parser.add_argument('--dry-run', action='store_true',
                        help="show what would change without writing anything")
    parser.add_argument('--root', default=REPO_ROOT,
                        help="labpack directory (default: the repo this script lives in)")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    new = args.new_name

    if not is_valid_identifier(new):
        sys.exit(f"'{new}' is not a valid Python package name: use letters, digits and "
                 f"underscores, and do not start with a digit.")
    if '-' in new:
        sys.exit(f"'{new}' contains a hyphen. Python packages use underscores "
                 f"(the *repository* may use hyphens; they need not match).")

    old = find_current_package(root)
    if old == new:
        sys.exit(f"The package is already called '{new}'. Nothing to do.")

    print(f"Renaming package '{old}' -> '{new}'\n  in {root}\n")

    # --- 1. content, across every text file -----------------------------------------------------
    edits = []
    for path in sorted(text_files(root)):
        result = rewrite(path, old, new)
        if result:
            changes, original, updated = result
            edits.append((path, changes, updated))

    if not edits:
        print("No references found. Renaming the directory only.")

    for path, changes, _ in edits:
        rel = os.path.relpath(path, root)
        print(f"  {rel}  ({len(changes)} line{'s' if len(changes) != 1 else ''})")
        for lineno, before, after in changes[:3]:
            print(f"      {lineno}: - {before.strip()}")
            print(f"      {lineno}: + {after.strip()}")
        if len(changes) > 3:
            print(f"      ... and {len(changes) - 3} more")

    # --- 2. the directory itself ----------------------------------------------------------------
    old_dir, new_dir = os.path.join(root, old), os.path.join(root, new)
    print(f"\n  {old}/ -> {new}/   (directory)")

    if args.dry_run:
        total = sum(len(c) for _, c, _ in edits)
        print(f"\nDry run: {total} line(s) across {len(edits)} file(s), plus the directory. "
              f"Nothing written.")
        return

    if os.path.exists(new_dir):
        sys.exit(f"\n{new_dir} already exists. Move it aside first.")

    for path, _, updated in edits:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated)

    # git mv keeps the rename in history (so a diff shows a move, not a delete plus an add).
    moved_with_git = False
    if os.path.isdir(os.path.join(root, '.git')):
        moved_with_git = subprocess.run(['git', '-C', root, 'mv', old, new],
                                        capture_output=True).returncode == 0
    if not moved_with_git:
        os.rename(old_dir, new_dir)

    print(f"\nDone. Now:")
    print(f"  pip install -e .          # reinstall under the new name")
    print(f"  pip uninstall {old}" + " " * max(0, 12 - len(old)) + "# if it was installed before")
    print(f"\nThen check it over: stimpack --check-labpack")


if __name__ == '__main__':
    main()
