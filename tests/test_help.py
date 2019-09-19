import re

from helpers import run

hlp = run('--help')
stdout = hlp.stdout


def test_usage():
    assert stdout.startswith('Usage: ghia.py [OPTIONS] REPOSLUG')


def test_description():
    assert (
        'CLI tool for automatic issue assigning of GitHub issues' in stdout
    )


def test_strategy():
    assert re.search(r'-s,\s+--strategy\s+\[append\|set\|change\]\s+'
                     r'How\s+to\s+handle\s+assignment\s+collisions\.'
                     r'\s+\[default:\s+append\]', stdout)


def test_dryrun():
    assert re.search(r'-d,\s+--dry-run\s+'
                     r'Run without making\s+any\s+changes\.',
                     stdout)


def test_config_auth():
    assert re.search(r'-a,\s+--config-auth\s+FILENAME\s+'
                     r'File with authorization\s+configuration\.'
                     r'\s+\[required\]', stdout)


def test_config_rules():
    assert re.search(r'-r,\s+--config-rules\s+FILENAME\s+'
                     r'File with assignment\s+rules\s+configuration\.'
                     r'\s+\[required\]', stdout)
