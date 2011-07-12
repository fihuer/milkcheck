#!/usr/bin/env python
# Copyright CEA (2011)
# Contributor: TATIBOUET Jeremie <tatibouetj@ocre.cea.fr>

"""
This is the entry point of MilkCheck
"""
import sys
from MilkCheck.UI.Cli import CommandLineInterface

if __name__ == "__main__":
    '''Entry point of MilkCheck'''
    cli = CommandLineInterface()
    sys.exit(cli.execute(sys.argv[1:]))