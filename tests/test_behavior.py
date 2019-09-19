from helpers import run, config, repo, issue_assignees, issue_labels, issue_set_labels, contains_exactly


def test_incorrect_token():
    # This test might end up well even if repo does not exist
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'--config-auth "{config("auth.fff.cfg")}" '
             f'{repo}')
    assert cp.returncode == 10
    assert len(cp.stdout) == 0
    assert f'ERROR: Could not list issues for repository {repo}' in cp.stderr


def test_nonexisting_repo():
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             'MarekSuchanek/NonExistingRepository')
    assert cp.returncode == 10
    assert len(cp.stdout) == 0
    assert 'ERROR: Could not list issues for repository MarekSuchanek/NonExistingRepository' in cp.stderr


def test_forbidden_repo_nochange():
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             'ghia-anna/awesome')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert f'-> ghia-anna/awesome#1 (https://github.com/ghia-anna/awesome/issues/1)\n' \
           '   = ghia-anna\n' in cp.stdout


def test_forbidden_repo_change():
    cp = run(f'--config-rules "{config("rules.forbidden_repo.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             'ghia-anna/awesome')
    assert cp.returncode == 0
    assert '-> ghia-anna/awesome#1 (https://github.com/ghia-anna/awesome/issues/1)' in cp.stdout
    assert '   ERROR: Could not update issue ghia-anna/awesome#1' in cp.stderr


def test_forbidden_repo_dry_run_append():
    cp = run(f'--config-rules "{config("rules.forbidden_repo.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             '--dry-run ghia-anna/awesome')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert '-> ghia-anna/awesome#1 (https://github.com/ghia-anna/awesome/issues/1)\n' \
           '   = ghia-anna\n' \
           '   + MarekSuchanek\n' in cp.stdout


def test_forbidden_repo_dry_run_set():
    cp = run(f'--config-rules "{config("rules.forbidden_repo.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             '--strategy set --dry-run ghia-anna/awesome')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert '-> ghia-anna/awesome#1 (https://github.com/ghia-anna/awesome/issues/1)\n' \
           '   = ghia-anna\n' in cp.stdout


def test_forbidden_repo_dry_run_change():
    cp = run(f'--config-rules "{config("rules.forbidden_repo.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             '--strategy change --dry-run ghia-anna/awesome')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert '-> ghia-anna/awesome#1 (https://github.com/ghia-anna/awesome/issues/1)\n' \
           '   - ghia-anna\n' \
           '   + MarekSuchanek\n' in cp.stdout


# Following tests actually change assignments
# Initially (8 assignments in open issues):
# #5 -> ghia-anna
# #7 -> ghia-anna, ghia-john
# #8 -> ghia-anna, ghia-peter
# #24 -> ghia-anna
# #52 -> ghia-anna (closed issue)
# #55 -> ghia-peter (closed issue)
# #117 -> ghia-anna
# #118 -> ghia-peter

def test_match_text():
    cp = run(f'--config-rules "{config("rules.match_text.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'{repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0  # default strategy = append
    assert cp.stdout.count('   = ') == 8
    assert cp.stdout.count('   + ') == 4  # (all below)
    assert f'-> {repo}#1 (https://github.com/{repo}/issues/1)\n' \
           f'   + ghia-anna\n' \
           f'   + ghia-jane\n' in cp.stdout
    assert contains_exactly(['ghia-anna', 'ghia-jane'], issue_assignees(repo, 1))
    assert f'-> {repo}#13 (https://github.com/{repo}/issues/13)\n' \
           f'   + ghia-jane\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#110 (https://github.com/{repo}/issues/110)\n' \
           f'   + ghia-jane\n' \
           f'->' in cp.stdout
    # closed issue
    assert f'-> {repo}#50 (https://github.com/{repo}/issues/50)\n' not in cp.stdout
    # label+title "trap"
    assert f'-> {repo}#46 (https://github.com/{repo}/issues/46)\n' \
           f'->' in cp.stdout
    assert [] == issue_assignees(repo, 50)
    assert [] == issue_assignees(repo, 46)


def test_match_title():
    cp = run(f'--config-rules "{config("rules.match_title.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'{repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0  # default strategy = append
    assert cp.stdout.count('   = ') == 12  # 8 initial + 4 from the previous test(s)
    assert cp.stdout.count('   + ') == 5  # (all below)
    assert f'-> {repo}#2 (https://github.com/{repo}/issues/2)\n' \
           f'   + ghia-anna\n' \
           f'   + ghia-peter\n' \
           f'->' in cp.stdout
    assert contains_exactly(['ghia-anna', 'ghia-peter'], issue_assignees(repo, 2))
    assert f'-> {repo}#27 (https://github.com/{repo}/issues/27)\n' \
           f'   + ghia-anna\n' \
           f'   + ghia-peter\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#111 (https://github.com/{repo}/issues/111)\n' \
           f'   + ghia-anna\n' \
           f'->' in cp.stdout
    # closed issue
    assert f'-> {repo}#51 (https://github.com/{repo}/issues/51)\n' not in cp.stdout
    # label+text "trap"
    assert f'-> {repo}#47 (https://github.com/{repo}/issues/47)\n' \
           f'->' in cp.stdout


def test_match_label():
    cp = run(f'--config-rules "{config("rules.match_label.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'{repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0  # default strategy = append
    assert cp.stdout.count('   = ') == 17  # 8 initial + 9 from the previous test(s)
    assert cp.stdout.count('   + ') == 4  # (all below)
    assert f'-> {repo}#3 (https://github.com/{repo}/issues/3)\n' \
           f'   + ghia-anna\n' \
           f'   + ghia-john\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#33 (https://github.com/{repo}/issues/33)\n' \
           f'   + ghia-john\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#112 (https://github.com/{repo}/issues/112)\n' \
           f'   + ghia-john\n' \
           f'->' in cp.stdout
    assert contains_exactly(['ghia-john'], issue_assignees(repo, 112))
    # closed issue
    assert f'-> {repo}#52 (https://github.com/{repo}/issues/52)\n' not in cp.stdout
    # title+text "trap"
    assert f'-> {repo}#48 (https://github.com/{repo}/issues/48)\n' \
           f'->' in cp.stdout


def test_match_any():
    cp = run(f'--config-rules "{config("rules.match_any.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'{repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0  # default strategy = append
    assert cp.stdout.count('   = ') == 21  # 8 initial + 13 from the previous test(s)
    assert cp.stdout.count('   + ') == 8  # (all below)
    assert f'-> {repo}#4 (https://github.com/{repo}/issues/4)\n' \
           f'   + ghia-anna\n' \
           f'   + ghia-peter\n' \
           f'->' in cp.stdout
    assert contains_exactly(['ghia-anna', 'ghia-peter'], issue_assignees(repo, 4))
    assert f'-> {repo}#15 (https://github.com/{repo}/issues/15)\n' \
           f'   + ghia-anna\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#17 (https://github.com/{repo}/issues/17)\n' \
           f'   + ghia-anna\n' \
           f'   + ghia-peter\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#96 (https://github.com/{repo}/issues/96)\n' \
           f'   + ghia-peter\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#113 (https://github.com/{repo}/issues/113)\n' \
           f'   + ghia-anna\n' \
           f'->' in cp.stdout
    # closed issue
    assert f'-> {repo}#53 (https://github.com/{repo}/issues/53)\n' not in cp.stdout


def test_fallback_label():
    labels_before = {
        6: [],
        9: [],
        21: [],
        46: ['Network'],
        47: ['Develop', 'Setup'],
        48: [],
        114: [],
        116: ['DB Migration', 'question'],
        119: []
    }
    cp = run(f'--config-rules "{config("rules.fallback_label.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--strategy append {repo}')
    labels_after = {
        i: issue_labels(repo, i) for i in labels_before.keys()
    }
    for i in labels_before.keys():
        # set the labels back for future testing
        issue_set_labels(repo, i, labels_before[i])
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0  # still strategy append
    assert cp.stdout.count('   = ') == 29  # 8 initial + 21 from the previous test(s)
    assert cp.stdout.count('   + ') == 0  # nothing can be added (empty patterns)
    assert cp.stdout.count('   FALLBACK: added label "Need assignment"') == 9
    assert cp.stdout.count('   FALLBACK: already has label "Need assignment"') == 82
    for i in labels_before.keys():
        assert f'-> {repo}#{i} (https://github.com/{repo}/issues/{i})\n' \
               f'   FALLBACK: added label "Need assignment"\n' \
               f'->' in cp.stdout
        assert contains_exactly(labels_before[i] + ['Need assignment'], labels_after[i])


def test_fallback_label_dry_run():
    # same as before, just dry-run so it should not actually set the label
    labels_before = {
        6: [],
        9: [],
        21: [],
        46: ['Network'],
        47: ['Develop', 'Setup'],
        48: [],
        114: [],
        116: ['DB Migration', 'question'],
        119: []
    }
    cp = run(f'--config-rules "{config("rules.fallback_label.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--dry-run {repo}')
    labels_after = {
        i: issue_labels(repo, i) for i in labels_before.keys()
    }
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0  # still strategy append
    assert cp.stdout.count('   = ') == 29  # 8 initial + 21 from the previous test(s)
    assert cp.stdout.count('   + ') == 0  # nothing can be added (empty patterns)
    assert cp.stdout.count('   FALLBACK: added label "Need assignment"') == 9
    assert cp.stdout.count('   FALLBACK: already has label "Need assignment"') == 82
    for i in labels_before.keys():
        assert f'-> {repo}#{i} (https://github.com/{repo}/issues/{i})\n' \
               f'   FALLBACK: added label "Need assignment"\n' \
               f'->' in cp.stdout
        assert contains_exactly(labels_before[i], labels_after[i])


def test_strategy_append():
    cp = run(f'--config-rules "{config("rules.strategy_append.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--strategy append {repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0  # still strategy append
    assert cp.stdout.count('   = ') == 29  # 8 initial + 21 from the previous test(s)
    assert cp.stdout.count('   + ') == 3  # (all below)
    assert f'-> {repo}#5 (https://github.com/{repo}/issues/5)\n' \
           f'   = ghia-anna\n' \
           f'   + ghia-jane\n' \
           f'->' in cp.stdout
    assert contains_exactly(['ghia-anna', 'ghia-jane'], issue_assignees(repo, 5))
    assert f'-> {repo}#24 (https://github.com/{repo}/issues/24)\n' \
           f'   = ghia-anna\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#116 (https://github.com/{repo}/issues/116)\n' \
           f'   + ghia-anna\n' \
           f'   + ghia-peter\n' \
           f'->' in cp.stdout
    # closed issue
    assert f'-> {repo}#55 (https://github.com/{repo}/issues/55)\n' not in cp.stdout


def test_strategy_set():
    cp = run(f'--config-rules "{config("rules.strategy_set.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--strategy set {repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0  # still strategy append
    assert cp.stdout.count('   = ') == 32  # 8 initial + 24 from the previous test(s)
    assert cp.stdout.count('   + ') == 2  # (all below)
    assert f'-> {repo}#6 (https://github.com/{repo}/issues/6)\n' \
           f'   + ghia-john\n' \
           f'   + ghia-peter\n' \
           f'->' in cp.stdout
    assert contains_exactly(['ghia-john', 'ghia-peter'], issue_assignees(repo, 6))
    assert f'-> {repo}#117 (https://github.com/{repo}/issues/117)\n' \
           f'   = ghia-anna\n' \
           f'->' in cp.stdout
    assert contains_exactly(['ghia-anna'], issue_assignees(repo, 117))
    # closed issue
    assert f'-> {repo}#56 (https://github.com/{repo}/issues/56)\n' not in cp.stdout


def test_strategy_change():
    cp = run(f'--config-rules "{config("rules.strategy_change.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--strategy change {repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count(f'-> {repo}#') == 112
    assert cp.stdout.count('   - ') == 31  # 31 + 3 = 34 from before (8 initial + 26 additional)
    assert cp.stdout.count('   = ') == 3  # (all below)
    assert cp.stdout.count('   + ') == 1  # (all below)
    assert f'-> {repo}#5 (https://github.com/{repo}/issues/5)\n' \
           f'   - ghia-anna\n' \
           f'   - ghia-jane\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#7 (https://github.com/{repo}/issues/7)\n' \
           f'   = ghia-anna\n' \
           f'   - ghia-john\n' \
           f'   + ghia-peter\n' \
           f'->' in cp.stdout
    assert contains_exactly(['ghia-anna', 'ghia-peter'], issue_assignees(repo, 7))
    assert f'-> {repo}#8 (https://github.com/{repo}/issues/8)\n' \
           f'   = ghia-anna\n' \
           f'   = ghia-peter\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#24 (https://github.com/{repo}/issues/24)\n' \
           f'   - ghia-anna\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#117 (https://github.com/{repo}/issues/117)\n' \
           f'   - ghia-anna\n' \
           f'->' in cp.stdout
    assert f'-> {repo}#118 (https://github.com/{repo}/issues/118)\n' \
           f'   - ghia-peter\n' \
           f'->' in cp.stdout
    assert [] == issue_assignees(repo, 118)
    # closed issue
    assert f'-> {repo}#57 (https://github.com/{repo}/issues/57)\n' not in cp.stdout


def test_assign_nonuser():
    cp = run(f'--config-rules "{config("rules.assign_nonuser.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'{repo}')
    assert cp.returncode == 0
    assert cp.stdout.count(f'-> {repo}#') == 112
    assert cp.stdout.count('   - ') == 0
    assert cp.stdout.count('   = ') == 4  # nothing is changed from the previous one
    assert cp.stdout.count('   + ') == 0
    assert f'-> {repo}#119 (https://github.com/{repo}/issues/119)\n' \
           f'->' in cp.stdout
    assert f'   ERROR: Could not update issue {repo}#119\n' == cp.stderr


def test_empty_append():
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--strategy append {repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0
    assert cp.stdout.count('   = ') == 4  # nothing is changed from the previous one
    assert cp.stdout.count('   + ') == 0
    assert f'-> {repo}#8 (https://github.com/{repo}/issues/8)\n' \
           f'   = ghia-anna\n' \
           f'   = ghia-peter\n' \
           f'->' in cp.stdout
    assert ['ghia-anna', 'ghia-peter'] == issue_assignees(repo, 8)


def test_empty_set():
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--strategy set {repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 0
    assert cp.stdout.count('   = ') == 4  # nothing is changed from the previous one
    assert cp.stdout.count('   + ') == 0
    assert f'-> {repo}#8 (https://github.com/{repo}/issues/8)\n' \
           f'   = ghia-anna\n' \
           f'   = ghia-peter\n' \
           f'->' in cp.stdout
    assert ['ghia-anna', 'ghia-peter'] == issue_assignees(repo, 8)
    assert f'-> {repo}#9 (https://github.com/{repo}/issues/9)\n' \
           f'->' in cp.stdout


def test_empty_change():
    cp = run(f'--config-rules "{config("rules.empty.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--strategy change {repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert cp.stdout.count('   - ') == 4  # remove the remaining
    assert cp.stdout.count('   = ') == 0
    assert cp.stdout.count('   + ') == 0
    assert f'-> {repo}#8 (https://github.com/{repo}/issues/8)\n' \
           f'   - ghia-anna\n' \
           f'   - ghia-peter\n' \
           f'->' in cp.stdout
    assert [] == issue_assignees(repo, 8)
    assert [] == issue_assignees(repo, 116)


def test_reset():
    # This test just tries to turn back all the issues back
    # it assumes that test_empty_change works as well
    cp = run(f'--config-rules "{config("rules.reset.cfg")}" '
             f'--config-auth "{config("auth.real.cfg")}" '
             f'--strategy change {repo}')
    assert cp.returncode == 0
    assert len(cp.stderr) == 0
    assert ['ghia-anna'] == issue_assignees(repo, 5)
    assert ['ghia-anna', 'ghia-john'] == issue_assignees(repo, 7)
    assert ['ghia-anna', 'ghia-peter'] == issue_assignees(repo, 8)
    assert ['ghia-anna'] == issue_assignees(repo, 24)
    assert ['ghia-anna'] == issue_assignees(repo, 117)
    assert ['ghia-peter'] == issue_assignees(repo, 118)

