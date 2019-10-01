import atexit
import contextlib
import os
import pathlib
import requests
import shlex
import subprocess
import sys


def run(line, **kwargs):
    print('$ python ghia.py', line)
    command = [sys.executable, 'ghia.py'] + shlex.split(line)
    return subprocess.run(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True,
                          **kwargs)


def run_ok(*args, **kwargs):
    cp = run(*args, **kwargs)
    assert cp.returncode == 0
    assert not cp.stderr
    print(cp.stdout)
    return cp


def config(name):
    return pathlib.Path(__file__).parent / 'fixtures' / name


@contextlib.contextmanager
def env(**kwargs):
    original = {key: os.getenv(key) for key in kwargs}
    os.environ.update({key: str(value) for key, value in kwargs.items()})
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                del os.environ[key]
            else:
                os.environ[key] = value


def contains_exactly(items, lst):
    return len(items) == len(lst) and all(i in lst for i in items)


try:
    user = os.environ['GITHUB_USER']
    token = os.environ['GITHUB_TOKEN']
    repo = f'mi-pyt-ghia/{user}'
except KeyError:
    raise RuntimeError('You must set GITHUB_USER and GITHUB_TOKEN environ vars')
else:
    config('auth.real.cfg').write_text(
        config('auth.fff.cfg').read_text().replace(40 * 'f', token)
    )
    config('auth.no-secret.real.cfg').write_text(
        config('auth.no-secret.cfg').read_text().replace(40 * 'f', token)
    )
    atexit.register(config('auth.real.cfg').unlink)
    atexit.register(config('auth.no-secret.real.cfg').unlink)


def issue_assignees(repo, issue_number):
    return [assignee['login'] for assignee in requests.get(
        f'https://api.github.com/repos/{repo}/issues/{issue_number}',
        headers={'Authorization': 'token ' + token},
    ).json()['assignees']]


def issue_labels(repo, issue_number):
    return [label['name'] for label in requests.get(
        f'https://api.github.com/repos/{repo}/issues/{issue_number}',
        headers={'Authorization': 'token ' + token},
    ).json()['labels']]


def issue_set_labels(repo, issue_number, labels):
    requests.patch(f'https://api.github.com/repos/{repo}/issues/{issue_number}',
                   headers={'Authorization': 'token ' + token},
                   json={'labels': labels})
