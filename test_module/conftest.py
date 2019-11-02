import configparser
import os
import pytest
import subprocess


ABS_PATH = os.path.abspath(os.path.dirname(__file__))
FIXTURES_PATH = os.path.join(ABS_PATH, 'fixtures')


class MissingConfigError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class Utils:

    def __init__(self, cfg, tmpdir, sh):
        self.cfg = cfg
        self.tmpdir = tmpdir
        self.sh = sh

    @property
    def package_info(self):
        # Run package_info script in virtual env
        return '{} {}'.format(self.python, os.path.join(FIXTURES_PATH, 'package_info.py'))

    @property
    def package_name(self):
        return self.cfg['vars']['testpypiname']

    @property
    def ghia_entrypoint(self):
        # Run entrypoint (should be in same path as python in virtual env)
        return os.path.join(self.venv, self.cfg['tests']['entrypoint'])

    @property
    def git(self):
        return self.cfg['commands']['git']

    @property
    def create_venv(self):
        return self.cfg['commands']['create_venv']

    @property
    def python(self):
        return str(self.tmpdir.join(self.cfg['commands']['python']))

    @property
    def venv(self):
        return os.path.split(self.python)[0]

    def venv_activate(self):
        os.environ['PATH'] = self.venv + ':' + os.environ['PATH']

    @property
    def pytest(self):
        return '{} -m {}'.format(self.python, self.cfg['commands']['pytest'])

    @property
    def pip(self):
        return '{} -m {}'.format(self.python, self.cfg['commands']['pip'])

    @property
    def pip_install_testpypi(self):
        return '{} -m {}'.format(self.python, self.cfg['commands']['pip_install_testpypi'])

    @property
    def repo_ssh(self):
        return self.cfg['vars']['repo_full']

    @property
    def repo_branch(self):
        return self.cfg['vars']['branch']

    def get_set(self, set_name):
        return frozenset(self.cfg.get('sets', set_name, fallback='').split(' '))

    def create_fresh_venv(self):
        result = self.sh(self.create_venv)
        assert result.was_successful, \
            'Could not create virtualenv for Python: {}'.format(result.stderr)
        self.sh(self.pip, 'install', '--upgrade', 'setuptools')
        self.sh(self.pip, 'install', '--upgrade', 'pip')

    def clone_repo(self, repo_dir):
        result = self.sh(self.git, 'clone', '-b', self.repo_branch, self.repo_ssh, repo_dir)
        assert result.was_successful, \
            'Could not clone the repository {}: {}'.format(self.repo_ssh, result.stderr)

    def clone_repo_with_fresh_venv(self, repo_dir):
        self.create_fresh_venv()
        self.clone_repo(repo_dir)


class ShellExecutionResult:
    def __init__(self, stdout, stderr, return_code):
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code

    @property
    def was_successful(self):
        return self.return_code == 0

    @property
    def outerr(self):
        return '{}\n{}\n{}'.format(self.stdout, '-'*80, self.stderr)


@pytest.fixture()
def config():
    ext_vars = {
        'GHIA_BRANCH': 'master'
    }
    ext_vars.update(os.environ)

    cfg = configparser.ConfigParser(ext_vars)
    cfg.read(os.path.join(FIXTURES_PATH, 'test_config.cfg'))

    if not cfg.has_option('vars', 'ctu_username'):
        raise MissingConfigError('CTU_USERNAME env var is missing!')
    if not cfg.has_option('vars', 'ghia_repo'):
        raise MissingConfigError('GHIA_REPO env var is missing!')
    if not cfg.has_option('vars', 'github_user'):
        raise MissingConfigError('GITHUB_USER env var is missing!')
    if not cfg.has_option('vars', 'github_token'):
        raise MissingConfigError('GITHUB_TOKEN env var is missing!')

    return cfg


@pytest.fixture()
def sh():
    def shell_executor(command, *args):
        p = subprocess.Popen(
            ' '.join([command, *args]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True
        )
        stdout, stderr = p.communicate()
        return ShellExecutionResult(stdout, stderr, p.returncode)
    return shell_executor


@pytest.fixture()
def utils(config, tmpdir, sh):
    return Utils(config, tmpdir, sh)
