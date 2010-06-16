# gozerlib/utils/web.py
#
#

""" google auth related functions. """

## gozerlib imports

from gozerlib.utils.trace import whichmodule

## google imports

from google.appengine.api import users as gusers

## basic imports

import logging

## functions

def finduser():
    """ try to find the email of the current logged in user. """
    user = gusers.get_current_user()
    if user:
        return user.email()

    return "" 

def checkuser(response, request, event=None):
    """
        check for user based on web response. first try google 
        otherwise return 'notath@IP' 

        :param response: response object
        :param request: request object
        :rtype: tuple of (userhost, gmail user, bot user , nick)

    """
    userhost = "notauth"
    u = "notauth"
    nick = "notauth"
    user = gusers.get_current_user()
    if event:
        hostid = "%s-%s" % (request.remote_addr, event.bot.uuid)
    else:
        hostid = request.remote_addr

    if not user:
        try:
            email = request.get('USER_EMAIL')
            if not email:
                email = "notauth"
            #logging.debug("gae.utils.auth - using %s" % str(request))
            auth_domain = request.get('AUTH_DOMAIN')
            who = request.get('who')
            if not who:
                 who = email
            if auth_domain:
                userhost = nick = "%s@%s" % (who, auth_domain)
            else:
                userhost = nick = "%s@%s" % (who, hostid)

        except KeyError:
            userhost = nick = "notauth@%s" % hostid
    else:
        userhost = user.email() 
        if not userhost:
            userhost = nick = "notauth@%s" % hostid
        nick = user.nickname()
        u = userhost

    cfrom = whichmodule()
    if 'gozerlib' in cfrom:
        cfrom = whichmodule(1)
        if 'gozerlib' in cfrom: 
            cfrom = whichmodule(2)

    logging.warn("auth - %s - %s - %s - %s - %s" % (cfrom, userhost, user, u, nick))
    return (userhost, user, u, nick)
