import flask
import importlib

from helpers import env, config, user

config_env = f'{config("auth.real.cfg")}:{config("rules.empty.cfg")}'
config_env_nosecret = f'{config("auth.no-secret.real.cfg")}:{config("rules.empty.cfg")}'


def _import_app():
    import ghia
    importlib.reload(ghia)  # force reload (config could change)
    if hasattr(ghia, 'app'):
        return ghia.app
    elif hasattr(ghia, 'create_app'):
        return ghia.create_app(None)
    else:
        raise RuntimeError(
            "Can't find a Flask app. "
            "Either instantiate `ghia.app` variable "
            "or implement `ghia.create_app(dummy)` function. "
            "See https://flask.palletsprojects.com/en/1.1.x/patterns/appfactories/"
            "for additional information."
        )


def _test_app():
    app = _import_app()
    app.config['TESTING'] = True
    return app.test_client()


def test_app_imports():
    with env(GHIA_CONFIG=config_env):
        app = _import_app()
        assert isinstance(app, flask.Flask)


def test_app_get_has_username():
    with env(GHIA_CONFIG=config_env):
        app = _test_app()
        assert user in app.get('/').get_data(as_text=True)


# If you change this, the Signature bellow must be updated!
PING = {
    'zen': 'Keep it logically awesome.',
    'hook_id': 123456,
    'hook': {
        'type': 'Repository',
        'id': 55866886,
        'name': 'web',
        'active': True,
        'events': [
            'issues',
        ],
        'config': {
            'content_type': 'json',
            'insecure_ssl': '0',
            'secret': '********',
        },
    },
    'repository': {
        'id': 123456,
        'name': 'ghia',
        'full_name': 'cvut/ghia',
        'private': False,
    },
    'sender': {
        'login': 'user',
    },
}


def test_ping_pongs():
    with env(GHIA_CONFIG=config_env):
        app = _test_app()
        rv = app.post('/', json=PING, headers={
            'X-Hub-Signature': 'sha1=d00e131ec9215b2a349ea1541e01e1a84ac38d8e',
            'X-GitHub-Event': 'ping'})
        assert rv.status_code == 200


def test_dangerous_ping_pong():
    with env(GHIA_CONFIG=config_env_nosecret):
        app = _test_app()
        rv = app.post('/', json=PING, headers={'X-GitHub-Event': 'ping'})
        assert rv.status_code == 200


def test_bad_secret():
    with env(GHIA_CONFIG=config_env):
        app = _test_app()
        rv = app.post('/', json=PING, headers={
            'X-Hub-Signature': 'sha1=1cacacc4207bdd4a51a7528bd9a5b9d6546b0c22',
            'X-GitHub-Event': 'ping'})
        assert rv.status_code >= 400
