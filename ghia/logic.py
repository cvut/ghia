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
