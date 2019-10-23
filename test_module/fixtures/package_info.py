import pkg_resources
import email
import json
import sys


def package_info_json(package_name):
    pkg_info = pkg_resources.get_distribution(package_name).get_metadata('PKG-INFO')
    info_items = email.message_from_string(pkg_info).items()
    return json.dumps(info_items)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('No package name as argument')
        sys.exit(2)
    data = package_info_json(sys.argv[1])
    print(data)
