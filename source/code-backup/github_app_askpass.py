#!/usr/bin/python3
"""Provide ephemeral app credentials only to GitHub HTTPS authentication prompts."""
import os
import sys


def answer(prompt, token):
    if not token:
        raise ValueError('No installation token')
    allowed = ("Username for 'https://github.com': ",
               "Password for 'https://x-access-token@github.com': ")
    if prompt == allowed[0]:
        return 'x-access-token'
    if prompt == allowed[1]:
        return token
    raise ValueError('Unapproved credential prompt')


if __name__ == '__main__':
    try:
        print(answer(sys.argv[1], os.environ.get('OPTIMA_GITHUB_INSTALLATION_TOKEN')))
    except (ValueError, IndexError):
        sys.exit(1)
