import re

from helpers import run

hlp_m = run('--help')
hlp_e = run('--help', entrypoint=True)
stdout_m = hlp_m.stdout
stdout_e = hlp_e.stdout


def test_usage():
    # tip: use cli(prog_name='ghia') when calling the click.command function
    assert stdout_m.startswith('Usage: ghia [OPTIONS] REPOSLUG')


def test_description():
    description = 'CLI tool for automatic issue assigning of GitHub issues'
    assert description in stdout_m
    assert description in stdout_e


def test_strategy():
    for stdout in stdout_m, stdout_e:
        assert re.search(r'-s,\s+--strategy\s+\[append\|set\|change\]\s+'
                         r'How\s+to\s+handle\s+assignment\s+collisions\.'
                         r'\s+\[default:\s+append\]', stdout)


def test_dryrun():
    for stdout in stdout_m, stdout_e:
        assert re.search(r'-d,\s+--dry-run\s+'
                         r'Run without making\s+any\s+changes\.',
                         stdout)


def test_config_auth():
    for stdout in stdout_m, stdout_e:
        assert re.search(r'-a,\s+--config-auth\s+FILENAME\s+'
                         r'File with authorization\s+configuration\.'
                         r'\s+\[required\]', stdout)


def test_config_rules():
    for stdout in stdout_m, stdout_e:
        assert re.search(r'-r,\s+--config-rules\s+FILENAME\s+'
                         r'File with assignment\s+rules\s+configuration\.'
                         r'\s+\[required\]', stdout)
