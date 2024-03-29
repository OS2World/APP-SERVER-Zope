##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
__doc__='''short description


$Id: SecurityManagement.py,v 1.7 2002/08/14 21:29:07 mj Exp $'''
__version__='$Revision: 1.7 $'[11:-2]

def getSecurityManager():
    """Get a security manager, for the current thread.
    """
    thread_id=get_ident()
    manager=_managers.get(thread_id, None)
    if manager is None:
        manager=SecurityManager(
            thread_id,
            SecurityContext(SpecialUsers.nobody))
        _managers[thread_id]=manager

    return manager

import SpecialUsers
from SecurityManager import SecurityManager
try:    import thread
except: get_ident=lambda: 0
else:   get_ident=thread.get_ident

_managers={}

def newSecurityManager(request, user):
    """Set up a new security context for a request for a user
    """
    thread_id=get_ident()
    _managers[thread_id]=SecurityManager(
        thread_id,
        SecurityContext(user),
        )

def noSecurityManager():
    try: del _managers[get_ident()]
    except: pass


def setSecurityPolicy(aSecurityPolicy):
    """Set the system default security policy.

    This method should only be caused by system startup code. It should
    never, for example, be called during a web request.
    """
    SecurityManager.setSecurityPolicy(aSecurityPolicy)

class SecurityContext:
    """The security context is an object used internally to the security
    machinery. It captures data about the current security context.
    """

    def __init__(self, user):
        self.stack=[]
        self.user=user
        self.objectCache = {}
