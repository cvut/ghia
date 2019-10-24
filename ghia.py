import configparser
import click
import flask
import hashlib
import hmac
import os
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
    return any(re.search(pattern, label['name'], re.IGNORECASE)
               for label in issue['labels'])


def _match_any(*args):
    return _match_title(*args) or _match_text(*args) or _match_label(*args)


class GHIA:

    STRATEGIES = {
        'append': _strategy_append,
        'set': _strategy_set,
        'change': _strategy_change
    }
    DEFAULT_STRATEGY = 'append'

    ENVVAR_STRATEGY = 'GHIA_STRATEGY'
    ENVVAR_DRYRUN = 'GHIA_DRYRUN'
    ENVVAR_CONFIG = 'GHIA_CONFIG'

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
        self.observers = dict()

    def add_observer(self, name, observer):
        self.observers[name] = observer

    def remove_observer(self, name):
        del self.observers[name]

    def call_observers(self, method, *args, **kwargs):
        for observer in self.observers.values():
            getattr(observer, method)(*args, **kwargs)

    @classmethod
    def _matches_pattern(cls, pattern, issue):
        t, p = pattern.split(':', 1)
        return cls.MATCHERS[t](p, issue)

    @classmethod
    def _matches(cls, patterns, issue):
        return any(cls._matches_pattern(pattern, issue)
                   for pattern in patterns)

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
            self.call_observers('fallbacked', self.fallback_label, True)
            labels.append(self.fallback_label)
            self._update_labels(owner, repo, issue, labels)
        else:
            self.call_observers('fallbacked', self.fallback_label, False)

    def run_issue(self, owner, repo, issue):
        self.call_observers('issue', owner, repo, issue)
        found_assignees = self._find_assignees(issue)
        old_assignees = [assignee['login'] for assignee in issue['assignees']]
        new_assignees = self.strategy(found_assignees, old_assignees)
        if old_assignees != new_assignees:  # there is a change
            self._update_assignees(owner, repo, issue, new_assignees)
        self.call_observers('assignees', old_assignees, new_assignees)
        if len(new_assignees) == 0:  # noone is assigned now
            self._create_fallback_label(owner, repo, issue)

    def run(self, owner, repo):
        try:
            issues = self.github.issues(owner, repo)
        except Exception:
            self.call_observers('error', f'Could not list issues '
                                         f'for repository {owner}/{repo}')
            exit(10)
            return

        for issue in issues:
            try:
                self.run_issue(owner, repo, issue)
            except Exception:
                number = issue['number']
                self.call_observers('error', f'Could not update issue '
                                             f'{owner}/{repo}#{number}', True)


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
        owner, repo = reposlug.split('/')
        return owner, repo
    except ValueError:
        raise click.BadParameter('not in owner/repository format')


@click.command('ghia')
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

###############################################################################
# WEB


def load_config_web(app):
    if GHIA.ENVVAR_CONFIG not in os.environ:
        app.logger.critical(f'Config not supplied by envvar {GHIA.ENVVAR_CONFIG}')
        exit(1)
    config_files = os.environ[GHIA.ENVVAR_CONFIG].split(':')
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(config_files)
    if not cfg.has_option('github', 'token'):
        app.logger.critical('Missing GitHub token in the given configuration')
        exit(1)
    app.config['github_token'] = cfg.get('github', 'token')
    app.config['github_secret'] = cfg.get('github', 'secret', fallback=None)

    try:
        patterns, fallback_label = parse_rules(cfg)
        app.config['patterns'] = patterns
        app.config['fallback_label'] = fallback_label
    except Exception:
        app.logger.critical('Incorrect rules configuration format')
        exit(1)


def webhook_verify_signature(payload, signature, secret, encoding='utf-8'):
    """
    Verify the payload with given signature against given secret
    see https://developer.github.com/webhooks/securing/
    payload: received data as dict
    signature: included SHA1 signature of payload (with secret)
    secret: secret to verify signature
    encoding: encoding for secret (optional)
    """
    h = hmac.new(secret.encode(encoding), payload, hashlib.sha1)
    return hmac.compare_digest('sha1=' + h.hexdigest(), signature)


GHIA.ISSUES_PROCESSED_ACTIONS = frozenset([
    'opened', 'edited', 'transferred', 'reopened',
    'assigned', 'unassigned', 'labeled', 'unlabeled'
])


def process_webhook_issues(payload):
    """
    Process webhook event "issue"
    payload: event payload
    """
    ghia = flask.current_app.config['ghia']
    reposlug = issue_number = ''
    try:
        action = payload['action']
        issue = payload['issue']
        issue_number = issue['number']
        reposlug = payload['repository']['full_name']
        owner, repo = reposlug.split('/')

        if action not in ghia.ISSUES_PROCESSED_ACTIONS:
            flask.current_app.logger.info(
                f'Action {action} from {reposlug}#{issue_number} skipped'
            )
            return 'Accepted but action not processed', 202

        if issue['state'] == 'open':
            ghia.run_issue(owner, repo, issue)

        flask.current_app.logger.info(
            f'Action {action} from {reposlug}#{issue_number} processed'
        )
        return 'Issue successfully processed', 200
    except (KeyError, IndexError):
        flask.current_app.logger.info(
            f'Incorrect data entity from IP {flask.request.remote_addr}'
        )
        flask.abort(422, 'Missing required payload fields')
    except Exception:
        flask.current_app.logger.error(
            f'Error occurred while processing {reposlug}#{issue_number}'
        )
        flask.abort(500, 'Issue processing error')


def process_webhook_ping(payload):
    """
    Process webhook event "ping"
    payload: event payload
    """
    try:
        repo = payload['repository']['full_name']
        hook_id = payload['hook_id']
        flask.current_app.logger.info(
            f'Accepting PING from {repo}#WH-{hook_id}'
        )
        return 'PONG', 200
    except KeyError:
        flask.current_app.logger.info(
            f'Incorrect data entity from IP {flask.request.remote_addr}'
        )
        flask.abort(422, 'Missing payload contents')


webhook_processors = {
    'issues': process_webhook_issues,
    'ping': process_webhook_ping
}


ghia_blueprint = flask.Blueprint('ghia', __name__)


@ghia_blueprint.route('/', methods=['GET'])
def index():
    return flask.render_template(
        'index.html.j2',
        rules=flask.current_app.config['patterns'],
        fallback_label=flask.current_app.config['fallback_label'],
        user=flask.current_app.config['github_user']
    )


@ghia_blueprint.route('/', methods=['POST'])
def webhook_listener():
    signature = flask.request.headers.get('X-Hub-Signature', '')
    event = flask.request.headers.get('X-GitHub-Event', '')
    payload = flask.request.get_json()

    secret = flask.current_app.config['github_secret']

    if secret is not None and not webhook_verify_signature(
            flask.request.data, signature, secret
    ):
        flask.current_app.logger.warning(
            f'Attempt with bad secret from IP {flask.request.remote_addr}'
        )
        flask.abort(401, 'Bad webhook secret')

    if event not in webhook_processors:
        supported = ', '.join(webhook_processors.keys())
        flask.abort(400, f'Event not supported (supported: {supported})')

    return webhook_processors[event](payload)


def create_app(*args, **kwargs):
    app = flask.Flask(__name__)

    app.logger.info('Loading GHIA configuration from files')
    load_config_web(app)

    app.logger.info('Loading GHIA strategy and ry-run configuration')
    strategy = os.environ.get(GHIA.ENVVAR_STRATEGY, GHIA.DEFAULT_STRATEGY)
    if strategy not in GHIA.STRATEGIES.keys():
        app.logger.critical(f'Unknown strategy "{strategy}" entered '
                            f'via envvar {GHIA.ENVVAR_STRATEGY}', err=True)
        exit(1)
    dry_run = configparser.ConfigParser.BOOLEAN_STATES.get(
        os.environ.get(GHIA.ENVVAR_DRYRUN, '0').lower(), False
    )

    app.logger.info(f'Preparing GHIA with strategy {strategy} and dry-run '
                    f'{"enabled" if dry_run else "disabled"}')

    app.config['ghia'] = GHIA(
        app.config['github_token'],
        app.config['patterns'],
        app.config['fallback_label'],
        dry_run,
        strategy
    )
    # Possible to add some observer app.logger
    try:
        app.logger.info('Getting GitHub user using the given token')
        app.config['github_user'] = app.config['ghia'].github.user()
    except Exception:
        app.logger.critical('Bad token: could not get GitHub user!', err=True)
        exit(1)

    app.register_blueprint(ghia_blueprint)

    return app

###############################################################################

# Both are possible to import "app" as well as "create_app"
app = None


if __name__ == '__main__':
    # Running as main file = CLI only
    cli()
else:
    # Being imported, setup the webapp
    app = create_app()
