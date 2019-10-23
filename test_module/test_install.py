import os
import pytest


@pytest.mark.parametrize('channel', ['GitHub', 'Test-PyPI'])
def test_install(utils, config, tmpdir, sh, channel):
    tmpdir.chdir()  # Work in separate tmp dir

    if channel == 'GitHub':  # Try to install from GitHub repository
        repo_dir = 'repo'
        # Prepare venv and clone repository to repo dir
        utils.clone_repo_with_fresh_venv(repo_dir)

        # Install with setup.py
        tmpdir.join(repo_dir).chdir()
        result = sh(utils.python, 'setup.py', 'install')
        assert result.was_successful, \
            'Could not install via setup.py: {}'.format(result.stderr)
        tmpdir.chdir()

    elif channel == 'Test-PyPI':  # Try to install from Test PyPI
        # Prepare venv for installing from PyPI
        utils.create_fresh_venv()

        testpypiname = config['vars']['testpypiname']
        result = sh(utils.pip_install_testpypi, testpypiname)
        assert result.was_successful, \
            'Could not install "{}" from Test PyPI'.format(testpypiname, result.stderr)

    else:
        raise LookupError('Unknown install channel')

    # Check installed requirements
    result = sh(utils.pip, 'freeze')
    assert result.was_successful, \
        'Command pip freeze failed'

    reqs = config['tests']['requirements'].split(' ')
    for req in reqs:
        assert req.lower() in result.outerr.lower(), \
            'Dependency was not installed: {}'.format(req)

    # Run with entrypoint
    result = sh(utils.ghia_entrypoint, '--help')
    assert result.was_successful, \
        'Invoking help via entrypoint failed'

    # Run as module (__main__)
    result = sh(utils.python, '-m', 'ghia', '--help')
    assert result.was_successful, \
        'Invoking help via module failed'

    # Clone tests (test installed ghia)
    tests_repo = config['tests']['repo']
    tests_branch = config['tests']['branch']
    tests_dir = 'tests'
    result = sh(utils.git, 'clone', '-b', tests_branch, tests_repo, tests_dir)
    assert result.was_successful, \
        'Cloning tests from {} was not successful: {}'.format(tests_repo, result.stderr)

    # Install test requirements
    reqs = config['tests']['test_requirements']
    result = sh(utils.pip, 'install', reqs)
    assert result.was_successful, \
        'Could not install test requirements: {}'.format(result.stderr)

    # Remove exported envvars affecting tests
    for e in utils.get_set('envvars'):
        if e in os.environ:
            del os.environ[e]
    # Simulate . env/bin/activate for sub-test's subprocess calls
    utils.venv_activate()
    # Run tests
    test_suites = config['tests']['tests'].split(' ')
    for test_suite in test_suites:
        result = sh(utils.pytest, tests_dir + '/' + test_suite, '-x')
        print(result.outerr)
        assert result.was_successful, \
            'Tests (pytest {}) failed'.format(test_suite)
