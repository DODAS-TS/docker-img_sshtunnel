#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function
from sys import argv, exit

def get_target_host(string):
    """Print and return the first address of the target.

    Example:
        "10.10.42.197 10.10.42.203 10.10.42.204" -> "10.10.42.197"
        "10.10.42.203" -> "10.10.42.203"
    """
    tmp = string.split(" ")[0]
    print(tmp, end="")
    return tmp

def main():
    get_target_host(argv[1])

if __name__ == '__main__':
    exit(main())
