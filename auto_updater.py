#!/usr/bin/env python3

"""
This module auto-updates from the GitHub repository at a regular interval.

Author:
Nikki Hess - nkhess@umich.edu
"""

no = False # lazy, will rename later

try:
    import git
except ImportError as e:
    no = True

import sys
import os
import time

def _restart_gui():
    os.execv(sys.executable, [sys.executable, "gui.py"])

def do_auto_update(interval_seconds: int):
    """
    Automatically check for updates via gitpython, restarts if needed
    Args:
        interval_seconds (int): the number of seconds between update checks
    """
    if not no:
        while True:
            # at the top to make sure it doesn't happen on startup
            time.sleep(interval_seconds)

            print("Checking for updates...")

            g = git.cmd.Git(os.getcwd())
            result = g.pull()

            print(result)

            # if we needed to update let's restart to apply changes
            if not "Already up to date." in result:
                _restart_gui()
            else:
                print("No updates found.")