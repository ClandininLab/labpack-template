"""scripts/rename_package.py and scripts/add_user.py, run on a scratch copy of this labpack.

Written without naming the package or stimulus directory literally, so the tests still mean the
same thing after a lab has renamed its copy (the rename script rewrites names across the repo).
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'scripts'))
import add_user  # noqa: E402
import rename_package  # noqa: E402

yaml = pytest.importorskip('yaml')


@pytest.fixture
def labpack(tmp_path):
    """A copy of this labpack without its git history, so renames are plain moves."""
    dst = tmp_path / 'labpack'
    shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.egg-info',
                                                             '.pytest_cache'))
    return str(dst)


def text_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in rename_package.SKIP_DIRS]
        for filename in filenames:
            if filename.endswith(rename_package.TEXT_SUFFIXES) and filename != 'rename_package.py':
                yield os.path.join(dirpath, filename)


def module_paths(cfg):
    for value in (cfg.get('module_paths') or {}).values():
        if isinstance(value, dict):
            value = list(value.values())
        for path in (value if isinstance(value, list) else [value]):
            path = path.split(':')[0] if not path.startswith('stimpack:') else None
            if path:
                yield path


@pytest.mark.parametrize('name, expected', [
    ('acme', ('acme_labpack', 'acme')),
    ('acme_labpack', ('acme_labpack', 'acme')),
    ('acmelab_pack', ('acmelab_pack', 'acmelab')),
])
def test_names(name, expected):
    assert rename_package.resolve_names(name) == expected


def test_dry_run_writes_nothing(labpack):
    before = {p: open(p, encoding='utf-8').read() for p in text_files(labpack)}
    rename_package.main(['acme', '--dry-run', '--root', labpack])
    after = {p: open(p, encoding='utf-8').read() for p in text_files(labpack)}
    assert before == after


def test_rename_moves_package_and_stim_dir_together(labpack):
    old_pkg = rename_package.find_current_package(labpack)
    [old_stim] = rename_package.find_stim_dirs(labpack, old_pkg)

    rename_package.main(['acme', '--root', labpack])

    assert rename_package.find_current_package(labpack) == 'acme_labpack'
    assert rename_package.find_stim_dirs(labpack, 'acme_labpack') == ['acme']

    stale_pkg = re.compile(rename_package.identifier(old_pkg))
    stale_stim = re.compile(rf'visual_stim[./]{re.escape(old_stim)}(?![A-Za-z0-9_])')
    for path in text_files(labpack):
        text = open(path, encoding='utf-8').read()
        assert not stale_pkg.search(text), f'{path} still names {old_pkg}'
        assert not stale_stim.search(text), f'{path} still names visual_stim/{old_stim}'

    for config in os.listdir(os.path.join(labpack, 'configs')):
        cfg = yaml.safe_load(open(os.path.join(labpack, 'configs', config), encoding='utf-8'))
        for path in module_paths(cfg):
            assert os.path.exists(os.path.join(labpack, path)), f'{config}: {path} does not exist'


def test_renamed_stimuli_still_import(labpack):
    """The failure this rename exists to prevent: stimuli.py importing a helper by a stale path."""
    pytest.importorskip('stimpack')
    pytest.importorskip('icosphere')
    rename_package.main(['acme', '--root', labpack])
    stimuli = os.path.join(labpack, 'acme_labpack', 'visual_stim', 'acme', 'stimuli.py')
    code = ("import importlib.util, sys; sys.path.insert(0, sys.argv[1]); "
            "s = importlib.util.spec_from_file_location('stimuli', sys.argv[2]); "
            "s.loader.exec_module(importlib.util.module_from_spec(s))")
    result = subprocess.run([sys.executable, '-c', code, labpack, stimuli],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# Ids no real lab member will have, so these run in a labpack that already has users.
USER, OTHER = 'zz_tester', 'zz_skeleton'


def test_add_user(labpack):
    rename_package.main(['acme', '--root', labpack])
    add_user.main([USER, '--name', 'Test Person', '--root', labpack])

    cfg = yaml.safe_load(open(os.path.join(labpack, 'configs', f'{USER}_config.yaml'),
                              encoding='utf-8'))
    assert cfg['experimenter'] == 'Test Person'
    assert cfg['parameter_presets_dir'] == f'presets/{USER}'
    assert f'acme_labpack/protocol/{USER}_protocol.py' in cfg['module_paths']['protocol']
    for path in module_paths(cfg):
        assert os.path.exists(os.path.join(labpack, path)), path
    assert os.path.isdir(os.path.join(labpack, 'presets', USER))

    # the new protocol module imports and its protocols build a trial
    sys.path.insert(0, labpack)
    try:
        spec = importlib.util.spec_from_file_location(
            f'{USER}_protocol', os.path.join(labpack, 'acme_labpack', 'protocol', f'{USER}_protocol.py'))
        module = importlib.util.module_from_spec(spec)
        pytest.importorskip('stimpack')
        spec.loader.exec_module(module)
        module.DriftingSquareGrating(cfg={}).get_trial_parameters()
    finally:
        sys.path.remove(labpack)
        for name in [m for m in sys.modules if m.split('.')[0] == 'acme_labpack']:
            del sys.modules[name]

    with pytest.raises(SystemExit):           # never overwrites
        add_user.main([USER, '--root', labpack])


def test_add_user_skeleton(labpack):
    rename_package.main(['acme', '--root', labpack])
    add_user.main([OTHER, '--empty', '--root', labpack])
    text = open(os.path.join(labpack, 'acme_labpack', 'protocol', f'{OTHER}_protocol.py')).read()
    assert 'from acme_labpack.protocol import base_protocol' in text
    compile(text, f'{OTHER}_protocol.py', 'exec')
