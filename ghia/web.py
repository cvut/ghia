import configparser
import flask
import hashlib
import hmac
import os

from ghia.logic import GHIA, parse_rules


def load_config_web(app):
    if GHIA.ENVVAR_CONFIG not in os.environ:
        app.logger.critical(f'Config not supplied by envvar {GHIA.ENVVAR_CONFIG}')
        exit(1)
    print(os.environ[GHIA.ENVVAR_CONFIG])
    config_files = os.environ[GHIA.ENVVAR_CONFIG].split(':')
    print(config_files)
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
        'index.html',
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

    try:
        app.logger.info('Getting GitHub user using the given token')
        app.config['github_user'] = app.config['ghia'].github.user()
    except Exception:
        app.logger.critical('Bad token: could not get GitHub user!', err=True)
        exit(1)

    app.register_blueprint(ghia_blueprint)

    return app
