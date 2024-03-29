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

"""WebDAV support - collection objects."""

__version__='$Revision: 1.24 $'[11:-2]

import sys, os,  Globals, davcmds, Lockable,re
from common import urlfix, rfc1123_date
from Resource import Resource
from AccessControl import getSecurityManager
from urllib import unquote
from WriteLockInterface import WriteLockInterface


class Collection(Resource):
    """The Collection class provides basic WebDAV support for
    collection objects. It provides default implementations
    for all supported WebDAV HTTP methods. The behaviors of some
    WebDAV HTTP methods for collections are slightly different
    than those for non-collection resources."""

    __dav_collection__=1

    def dav__init(self, request, response):
        # We are allowed to accept a url w/o a trailing slash
        # for a collection, but are supposed to provide a
        # hint to the client that it should be using one.
        # [WebDAV, 5.2]
        pathinfo=request.get('PATH_INFO','')
        if pathinfo and pathinfo[-1] != '/':
            location='%s/' % request['URL1']
            response.setHeader('Content-Location', location)
        response.setHeader('Connection', 'close', 1)
        response.setHeader('Date', rfc1123_date(), 1)
        response.setHeader('MS-Author-Via', 'DAV')

    def HEAD(self, REQUEST, RESPONSE):
        """Retrieve resource information without a response body."""
        self.dav__init(REQUEST, RESPONSE)
        # Note that we are willing to acquire the default document
        # here because what we really care about is whether doing
        # a GET on this collection / would yield a 200 response.
        if hasattr(self, 'index_html'):
            if hasattr(self.index_html, 'HEAD'):
                return self.index_html.HEAD(REQUEST, RESPONSE)
            raise 'Method Not Allowed', (
                  'Method not supported for this resource.'
                  )
        raise 'Not Found', 'The requested resource does not exist.'

    def PUT(self, REQUEST, RESPONSE):
        """The PUT method has no inherent meaning for collection
        resources, though collections are not specifically forbidden
        to handle PUT requests. The default response to a PUT request
        for collections is 405 (Method Not Allowed)."""
        self.dav__init(REQUEST, RESPONSE)
        raise 'Method Not Allowed', 'Method not supported for collections.'

    def DELETE(self, REQUEST, RESPONSE):
        """Delete a collection resource. For collection resources, DELETE
        may return either 200 (OK) or 204 (No Content) to indicate total
        success, or may return 207 (Multistatus) to indicate partial
        success. Note that in Zope a DELETE currently never returns 207."""


        self.dav__init(REQUEST, RESPONSE)
        ifhdr = REQUEST.get_header('If', '')
        url = urlfix(REQUEST['URL'], 'DELETE')
        name = unquote(filter(None, url.split( '/'))[-1])
        parent = self.aq_parent
        user = getSecurityManager().getUser()
        token = None

#        if re.match("/Control_Panel",REQUEST['PATH_INFO']):
#            RESPONSE.setStatus(403)
#            RESPONSE.setHeader('Content-Type', 'text/xml; charset="utf-8"')
#            return RESPONSE

        # Level 1 of lock checking (is the collection or its parent locked?)
        if Lockable.wl_isLocked(self):
            if ifhdr:
                self.dav__simpleifhandler(REQUEST, RESPONSE, 'DELETE', col=1)
            else:
                raise 'Locked'
        elif Lockable.wl_isLocked(parent):
            if ifhdr:
                parent.dav__simpleifhandler(REQUEST, RESPONSE, 'DELETE', col=1)
            else:
                raise 'Precondition Failed'
        # Second level of lock\conflict checking (are any descendants locked,
        # or is the user not permitted to delete?).  This results in a
        # multistatus response
        if ifhdr:
            tokens = self.wl_lockTokens()
            for tok in tokens:
                # We already know that the simple if handler succeeded,
                # we just want to get the right token out of the header now
                if ifhdr.find(tok) > -1:
                    token = tok
        cmd = davcmds.DeleteCollection()
        result = cmd.apply(self, token, user, REQUEST['URL'])

        if result:
            # There were conflicts, so we need to report them
            RESPONSE.setStatus(207)
            RESPONSE.setHeader('Content-Type', 'text/xml; charset="utf-8"')
            RESPONSE.setBody(result)
        else:
            # There were no conflicts, so we can go ahead and delete
            # ajung: additional check if we really could delete the collection
            # (Collector #2196)
            if parent.manage_delObjects([name],REQUEST=None)  is None:
                RESPONSE.setStatus(204)
            else:
                RESPONSE.setStatus(403)

        return RESPONSE


Globals.default__class_init__(Collection)
