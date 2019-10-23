import json
import tarfile
import glob
import os


def test_sdist(utils, tmpdir, sh):
    tmpdir.chdir()  # Work in separate tmp dir

    repo_dir = 'repo'
    # Prepare venv and clone repository to repo dir
    utils.clone_repo_with_fresh_venv(repo_dir)

    # Sdist with setup.py
    tmpdir.join(repo_dir).chdir()
    result = sh(utils.python, 'setup.py', 'sdist')
    assert result.was_successful, \
        'Could not sdist via setup.py: {}'.format(result.stderr)

    assert 'warning' not in result.outerr, \
        'There are some warnings in sdist output'

    # Check content of distributed .tar.gz file
    tmpdir.join(repo_dir).join('dist').chdir()
    dist_tgz_files = glob.glob('*.tar.gz')
    assert len(dist_tgz_files) != 0, \
        'No dist .tar.gz file has been produced'
    distfile = dist_tgz_files[0]

    tar_dist = tarfile.open(distfile)
    counts = {
        'license': 0,
        'template_html': 0,
        'readme': 0
    }
    for info in tar_dist.getmembers():
        if not info.isfile():
            continue
        path, file = os.path.split(info.name)
        if file in utils.get_set('license'):
            if info.size > 0:
                counts['license'] += 1
        elif file in utils.get_set('readme'):
            if info.size > 0:
                counts['readme'] += 1
        elif file.endswith(('.html', '.j2')) and path.endswith('templates'):
            # Sorry if you are using some custom name for templates dir
            if info.size > 0:
                counts['template_html'] += 1

    # There should be exactly one non-empty license info file
    assert counts['license'] > 0, \
        'No LICENSE/COPYING file provided in distributed .tar.gz'
    assert counts['license'] == 1, \
        'Multiple LICENSE/COPYING files provided in distributed .tar.gz'

    # There should be exactly one non-empty readme file
    assert counts['readme'] > 0, \
        'No README(.md,.rst) file provided in distributed .tar.gz'
    assert counts['readme'] == 1, \
        'Multiple README(.md,.rst) files provided in distributed .tar.gz'

    # There should be some HTML templates for web app
    assert counts['template_html'] > 0, \
        'No web app templates included in distributed .tar.gz'


def test_package_info(utils, tmpdir, sh):
    tmpdir.chdir()  # Work in separate tmp dir

    repo_dir = 'repo'
    # Prepare venv and clone repository to repo dir
    utils.clone_repo_with_fresh_venv(repo_dir)

    # Sdist with setup.py
    tmpdir.join(repo_dir).chdir()
    result = sh(utils.python, 'setup.py', 'install')
    assert result.was_successful, \
        'Could not sdist via setup.py: {}'.format(result.stderr)
    tmpdir.chdir()

    # Read package metadata via external script (in fixtures)
    result = sh(utils.package_info, utils.package_name)
    assert result.was_successful, \
        'Could not retrieve information about package {}'.format(utils.package_name)

    info_items = json.loads(result.stdout)

    classifiers = [x[1] for x in info_items if x[0] == 'Classifier']
    assert len(classifiers) > 4, 'Need to have at least 5 classifiers'
    assert 'Framework :: Flask' in classifiers
    assert 'Environment :: Console' in classifiers
    assert 'Environment :: Web Environment' in classifiers

    mandatory = ['Author', 'Author-email', 'License', 'Name', 'Summary',
                 'Description', 'Keywords', 'Version']
    values = {k: '' for k in mandatory}
    for m in mandatory:
        found = False
        for item in info_items:
            if item[0] == m:
                values[m] = item[1]
                found = True
                assert len(item[1]) > 0, 'Metadata {} is empty'.format(m)
                break
        assert found, 'Metadata {} is not present'.format(m)

    # Check name, version, keywords as @hroncok mentioned during tutorials
    assert values['Name'] == utils.package_name.replace('_', '-'), \
        'Bad package name in metadata'
    assert values['Version'].startswith('0.3'), \
        'Bad package version in metadata'
    keywords = values['Keywords'].replace(',', ' ').split(' ')
    keywords = [k for k in keywords if k != '']
    assert len(keywords) > 3, \
        'Less than 4 package keywords in metadata'
