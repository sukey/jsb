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

version = "0.8 DEVELOPMENT"

## getversion function

def getversion(txt=""):
    """ return a version string. """
    try: 
        from mercurial import context, hg, node, repo, ui
        repository = hg.repository(ui.ui(), '.')
        ctx = context.changectx(repository)
        tip = str(ctx.rev())
    except: tip = None
    if tip: version2 = version + " HG " + tip
    else: version2 = version
    if txt: return "JSONBOT %s %s" % (version2, txt)
    else: return "JSONBOT %s" % version2
