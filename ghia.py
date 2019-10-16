import configparser
import click
import re
import requests


class GitHub:
    """
    This class can communicate with the GitHub API
    just give it a token and go.
    """
    API = 'https://api.github.com'

    def __init__(self, token, session=None):
        """
        token: GitHub token
        session: optional requests session
        """
        self.token = token
        self.session = session or requests.Session()
        self.session.headers = {'User-Agent': 'python/ghia'}
        self.session.auth = self._token_auth

    def _token_auth(self, req):
        """
        This alters all our outgoing requests
        """
        req.headers['Authorization'] = 'token ' + self.token
        return req

    def _paginated_json_get(self, url, params=None):
        r = self.session.get(url, params=params)
        r.raise_for_status()
        json = r.json()
        if 'next' in r.links and 'url' in r.links['next']:
            json += self._paginated_json_get(r.links['next']['url'], params)
        return json

    def user(self):
        """
        Get current user authenticated by token
        """
        return self._paginated_json_get(f'{self.API}/user')

    def issues(self, owner, repo, state='open', assignee=None):
        """
        Get issues of a repo
        owner: GitHub user or org
        repo: repo name
        state: open, closed, all (default open)
        assignee: optional filter for assignees (None, "none", "<username>", or "*")
        """
        params = {'state': state}
        if assignee is not None:
            params['assignee'] = assignee
        url = f'{self.API}/repos/{owner}/{repo}/issues'
        return self._paginated_json_get(url, params)

    def set_issue_assignees(self, owner, repo, number, assignees):
        """
        Sets assignees for the issue. Replaces all existing assignees.
        owner: GitHub user or org
        repo: repo name
        number: issue id
        assignees: list of usernames (as strings)
        """
        url = f'{self.API}/repos/{owner}/{repo}/issues/{number}'
        r = self.session.patch(url, json={'assignees': assignees})
        r.raise_for_status()
        return r.json()['assignees']

    def set_issue_labels(self, owner, repo, number, labels):
        """
        Sets labels for the issue. Replaces all existing labels.
        owner: GitHub user or org
        repo: repo name
        number: issue id
        labels: list of labels (as strings)
        """
        url = f'{self.API}/repos/{owner}/{repo}/issues/{number}'
        r = self.session.patch(url, json={'labels': labels})
        r.raise_for_status()
        return r.json()['labels']


class Printer:

    @staticmethod
    def print_issue(owner, repo, issue):
        number, url = issue['number'], issue['html_url']
        identifier = click.style(f'{owner}/{repo}#{number}', bold=True)
        click.echo(f'-> {identifier} ({url})')

    @staticmethod
    def print_assignees(old, new):
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
    def print_fallbacked(label, added=True):
        prefix = click.style('FALLBACK', fg='yellow', bold=True)
        click.echo('   ', nl=False)
        message = 'added label' if added else 'already has label'
        click.echo(f'{prefix}: {message} "{label}"')

    @staticmethod
    def print_error(message, of_issue=False):
        prefix = click.style('ERROR', bold=True, fg='red')
        if of_issue:
            click.echo('   ', nl=False, err=True)
        click.echo(f'{prefix}: {message}', err=True)


def _strategy_append(found, old):
    return old + [a for a in found if a not in old]


def _strategy_set(found, old):
    return found if len(old) == 0 else old


def _strategy_change(found, old):
    return found


def _match_title(pattern, issue):
    return re.search(pattern, issue['title'], re.IGNORECASE)


def _match_text(pattern, issue):
    return re.search(pattern, issue['body'], re.IGNORECASE)


def _match_label(pattern, issue):
    return any(re.search(pattern, label['name'], re.IGNORECASE) for label in issue['labels'])


def _match_any(*args):
    return _match_title(*args) or _match_text(*args) or _match_label(*args)


class GHIA:

    STRATEGIES = {
        'append': _strategy_append,
        'set': _strategy_set,
        'change': _strategy_change
    }

    MATCHERS = {
        'any': _match_any,
        'text': _match_text,
        'title': _match_title,
        'label': _match_label
    }

    def __init__(self, token, rules, fallback_label, dry_run, ghia_strategy):
        self.github = GitHub(token)
        self.rules = rules
        self.fallback_label = fallback_label
        self.real_run = not dry_run
        self.strategy = self.STRATEGIES[ghia_strategy]

    @classmethod
    def _matches_pattern(cls, pattern, issue):
        t, p = pattern.split(':', 1)
        return cls.MATCHERS[t](p, issue)

    @classmethod
    def _matches(cls, patterns, issue):
        return any(cls._matches_pattern(pattern, issue) for pattern in patterns)

    def _find_assignees(self, issue):
        return [username
                for username, patterns in self.rules.items()
                if self._matches(patterns, issue)
                ]

    def _make_new_assignees(self, found, old):
        return self.strategy(found, old)

    def _update_assignees(self, owner, repo, issue, assignees):
        if self.real_run:
            self.github.set_issue_assignees(owner, repo, issue['number'], assignees)

    def _update_labels(self, owner, repo, issue, labels):
        if self.real_run:
            self.github.set_issue_labels(owner, repo, issue['number'], labels)

    def _create_fallback_label(self, owner, repo, issue):
        if self.fallback_label is None:
            return  # no fallback
        labels = [label['name'] for label in issue['labels']]
        if self.fallback_label not in labels:
            Printer.print_fallbacked(self.fallback_label, True)
            labels.append(self.fallback_label)
            self._update_labels(owner, repo, issue, labels)
        else:
            Printer.print_fallbacked(self.fallback_label, False)

    def _run_issue(self, owner, repo, issue):
        Printer.print_issue(owner, repo, issue)
        found_assignees = self._find_assignees(issue)
        old_assignees = [assignee['login'] for assignee in issue['assignees']]
        new_assignees = self.strategy(found_assignees, old_assignees)
        if old_assignees != new_assignees:  # there is a change
            self._update_assignees(owner, repo, issue, new_assignees)
        Printer.print_assignees(old_assignees, new_assignees)
        if len(new_assignees) == 0:  # noone is assigned now
            self._create_fallback_label(owner, repo, issue)

    def run(self, owner, repo):
        try:
            issues = self.github.issues(owner, repo)
        except Exception:
            Printer.print_error(f'Could not list issues for repository {owner}/{repo}')
            exit(10)
            return

        for issue in issues:
            try:
                self._run_issue(owner, repo, issue)
            except Exception:
                number = issue['number']
                Printer.print_error(f'Could not update issue {owner}/{repo}#{number}', True)


def parse_rules(cfg):
    """
    Parse labels to dict where label is key and list
    of patterns is corresponding value
    cfg: ConfigParser with loaded configuration of labels
    """
    patterns = {
        username: list(filter(None, cfg['patterns'][username].splitlines()))
        for username in cfg['patterns']
    }
    fallback = cfg.get('fallback', 'label', fallback=None)
    for user_patterns in patterns.values():
        for pattern in user_patterns:
            t, p = pattern.split(':', 1)
            assert t in GHIA.MATCHERS.keys()
    return patterns, fallback


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
        if re.match('[a-zA-Z0-9][a-zA-Z0-9\-]{0,38}/[a-zA-Z0-9\-_.]+', reposlug):
            return reposlug.split('/')
        else:
            raise ValueError('Invalid reposlug')
    except ValueError:
        raise click.BadParameter('not in owner/repository format')


@click.command('ghia')
@click.argument('reposlug', type=click.STRING, callback=parse_reposlug)
@click.option('-s', '--strategy', default='append', show_default=True,
              type=click.Choice(GHIA.STRATEGIES.keys()),
              help='How to handle assignment collisions.')
@click.option('--dry-run', '-d', is_flag=True,
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
    ghia.run(owner, repo)


if __name__ == '__main__':
    cli()
