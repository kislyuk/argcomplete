#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argparse
import pprint

import requests

import argcomplete


def github_org_members(prefix, parsed_args, **kwargs):
    resource = f"https://api.github.com/orgs/{parsed_args.organization}/members"
    return (member["login"] for member in requests.get(resource).json() if member["login"].startswith(prefix))


parser = argparse.ArgumentParser()
parser.add_argument("--organization", help="GitHub organization")
parser.add_argument("--member", help="GitHub member").completer = github_org_members

argcomplete.autocomplete(parser)
args = parser.parse_args()

pprint.pprint(requests.get(f"https://api.github.com/users/{args.member}").json())
