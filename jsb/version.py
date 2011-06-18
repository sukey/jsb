# jsb/version.py
#
#

""" version related stuff. """

## jsb imports

from jsb.lib.datadir import getdatadir

## basic imports

import os
import binascii

## defines

version = "0.7.1.3 RELEASE"

## getversion function

def getversion(txt=""):
    """ return a version string. """
    if txt: return "JSONBOT %s %s" % (version, txt)
    else: return "JSONBOT %s" % version
