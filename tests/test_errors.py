from helpers import run, config


def test_no_reposlug():
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'--config-auth "{config("auth.fff.cfg")}"')
    assert cp.returncode != 0
    assert not cp.stdout
    assert 'Error: Missing argument "REPOSLUG".' in cp.stderr


def test_no_config():
    cp = run('user/repo')
    assert cp.returncode != 0
    assert not cp.stdout
    assert (
        'Error: Missing option "-a" / "--config-auth".' in cp.stderr or
        'Error: Missing option "-r" / "--config-rules".' in cp.stderr
    )


def test_no_auth_config():
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'user/repo')
    assert cp.returncode != 0
    assert not cp.stdout
    assert 'Error: Missing option "-a" / "--config-auth".' in cp.stderr


def test_unusable_auth_config():
    cp = run(f'--config-auth "{config("empty_file.cfg")}" '
             f'--config-rules "{config("rules.empty.cfg")}" '
             f'user/repo')
    assert cp.returncode != 0
    assert not cp.stdout
    assert 'Error: Invalid value for "-a" / "--config-auth": incorrect configuration format' in cp.stderr


def test_no_labels_config():
    cp = run(f'--config-auth "{config("auth.fff.cfg")}" '
             f'user/repo')
    assert cp.returncode != 0
    assert not cp.stdout
    assert 'Error: Missing option "-r" / "--config-rules".' in cp.stderr


def test_unusable_labels_config():
    cp = run(f'--config-rules "{config("empty_file.cfg")}" '
             f'--config-auth "{config("auth.fff.cfg")}" '
             f'user/repo')
    assert cp.returncode != 0
    assert not cp.stdout
    assert '"-r" / "--config-rules": incorrect configuration format' in cp.stderr


def test_invalid_reposlug():
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'--config-auth "{config("auth.fff.cfg")}" '
             'foobar')
    assert cp.returncode != 0
    assert not cp.stdout
    assert 'Error: Invalid value for "REPOSLUG": not in owner/repository format' in cp.stderr
