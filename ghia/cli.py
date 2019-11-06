import click
import configparser

from ghia.logic import GHIA, parse_rules


class PrinterObserver:

    @staticmethod
    def issue(owner, repo, issue):
        number, url = issue['number'], issue['html_url']
        identifier = click.style(f'{owner}/{repo}#{number}', bold=True)
        click.echo(f'-> {identifier} ({url})')

    @staticmethod
    def assignees(old, new):
        mi = click.style('-', fg='red', bold=True)
        pl = click.style('+', fg='green', bold=True)
        eq = click.style('=', fg='blue', bold=True)
        assignees = list(set(old).union(set(new)))
        assignees.sort(key=lambda a: a.lower())
        for assignee in assignees:
            sign = eq
            if assignee not in old:
                sign = pl
            elif assignee not in new:
                sign = mi
            click.echo(f'   {sign} {assignee}')

    @staticmethod
    def fallbacked(label, added=True):
        prefix = click.style('FALLBACK', fg='yellow', bold=True)
        click.echo('   ', nl=False)
        message = 'added label' if added else 'already has label'
        click.echo(f'{prefix}: {message} "{label}"')

    @staticmethod
    def error(message, of_issue=False):
        prefix = click.style('ERROR', bold=True, fg='red')
        if of_issue:
            click.echo('   ', nl=False, err=True)
        click.echo(f'{prefix}: {message}', err=True)



def get_rules(ctx, param, config_rules):
    """
    Extract labels from labels config and do the checks
    config_rules: ConfigParser with loaded configuration of labels
    """
    try:
        cfg_rules = configparser.ConfigParser()
        cfg_rules.optionxform = str
        cfg_rules.read_file(config_rules)
        return parse_rules(cfg_rules)
    except Exception:
        raise click.BadParameter('incorrect configuration format')


def get_token(ctx, param, config_auth):
    """
    Extract token from auth config and do the checks
    config_auth: ConfigParser with loaded configuration of auth
    """
    try:
        cfg_auth = configparser.ConfigParser()
        cfg_auth.read_file(config_auth)
        return cfg_auth.get('github', 'token')
    except Exception:
        raise click.BadParameter('incorrect configuration format')


def parse_reposlug(ctx, param, reposlug):
    try:
        owner, repo = reposlug.split('/')
        return owner, repo
    except ValueError:
        raise click.BadParameter('not in owner/repository format')


@click.command(name='ghia')
@click.argument('reposlug', type=click.STRING, callback=parse_reposlug)
@click.option('-s', '--strategy', default=GHIA.DEFAULT_STRATEGY,
              show_default=True, type=click.Choice(GHIA.STRATEGIES.keys()),
              envvar=GHIA.ENVVAR_STRATEGY,
              help='How to handle assignment collisions.')
@click.option('--dry-run', '-d', is_flag=True, envvar=GHIA.ENVVAR_DRYRUN,
              help='Run without making any changes.')
@click.option('-a', '--config-auth', type=click.File('r'), callback=get_token,
              help='File with authorization configuration.', required=True)
@click.option('-r', '--config-rules', type=click.File('r'), callback=get_rules,
              help='File with assignment rules configuration.', required=True)
def cli(reposlug, strategy, dry_run, config_auth, config_rules):
    """CLI tool for automatic issue assigning of GitHub issues"""
    token = config_auth
    rules, fallback_label = config_rules
    owner, repo = reposlug
    ghia = GHIA(token, rules, fallback_label, dry_run, strategy)
    ghia.add_observer('printer', PrinterObserver)
    ghia.run(owner, repo)
