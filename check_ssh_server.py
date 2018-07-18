#!/usr/bin/env python3
from paramiko import (AuthenticationException, AutoAddPolicy,
                      BadHostKeyException, SSHException)
from paramiko.client import SSHClient
from os import environ


def main():
    try:
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy)
        client.connect(environ.get('TARGET_HOST', 'localhost'),
                       port=environ.get('TARGET_SSH_PORT', 31042),
                       username="admin", password="passwd")
    except (BadHostKeyException, AuthenticationException,
            SSHException):
        return 1
    return 0


if __name__ == '__main__':
    exit(main())
