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
"""Filesystem Page Template module

Zope object encapsulating a Page Template from the filesystem.
"""

__version__='$Revision: 1.20.2.2 $'[11:-2]

import os, AccessControl, Acquisition, sys
from Globals import package_home, DevelopmentMode
from zLOG import LOG, ERROR, INFO
from Shared.DC.Scripts.Script import Script, BindingsUI
from Shared.DC.Scripts.Signature import FuncCode
from AccessControl import getSecurityManager
from OFS.Traversable import Traversable
from PageTemplate import PageTemplate
from Expressions import SecureModuleImporter
from ComputedAttribute import ComputedAttribute
from ExtensionClass import Base
from Acquisition import aq_parent, aq_inner

class PageTemplateFile(Script, PageTemplate, Traversable):
    "Zope wrapper for filesystem Page Template using TAL, TALES, and METAL"

    meta_type = 'Page Template (File)'

    func_defaults = None
    func_code = FuncCode((), 0)
    _need__name__=1
    _v_last_read=0

    _default_bindings = {'name_subpath': 'traverse_subpath'}

    security = AccessControl.ClassSecurityInfo()
    security.declareProtected('View management screens',
      'read', 'document_src')

    def __init__(self, filename, _prefix=None, **kw):
        self.ZBindings_edit(self._default_bindings)
        if _prefix is None: _prefix=SOFTWARE_HOME
        elif type(_prefix) is not type(''):
            _prefix = package_home(_prefix)
        name = kw.get('__name__')
        if name:
            self._need__name__ = 0
            self.__name__ = name
        else:
            self.__name__ = os.path.splitext(os.path.split(filename)[-1])[0]
        if not os.path.splitext(filename)[1]:
            filename = filename + '.zpt'
        self.filename = os.path.join(_prefix, filename)

    def pt_getContext(self):
        root = self.getPhysicalRoot()
        c = {'template': self,
             'here': self._getContext(),
             'container': self._getContainer(),
             'nothing': None,
             'options': {},
             'root': root,
             'request': getattr(root, 'REQUEST', None),
             'modules': SecureModuleImporter,
             }
        return c

    def _exec(self, bound_names, args, kw):
        """Call a Page Template"""
        self._cook_check()
        if not kw.has_key('args'):
            kw['args'] = args
        bound_names['options'] = kw

        try:
            response = self.REQUEST.RESPONSE
            if not response.headers.has_key('content-type'):
                response.setHeader('content-type', self.content_type)
        except AttributeError:
            pass

        # Execute the template in a new security context.
        security=getSecurityManager()
        bound_names['user'] = security.getUser()
        security.addContext(self)
        try:
            return self.pt_render(extra_context=bound_names)
        finally:
            security.removeContext(self)

    def pt_macros(self):
        self._cook_check()
        return PageTemplate.pt_macros(self)

    def pt_source_file(self):
        """Returns a file name to be compiled into the TAL code."""
        return self.__name__  # Don't reveal filesystem paths

    def _cook_check(self):
        if self._v_last_read and not DevelopmentMode:
            return
        __traceback_info__ = self.filename
        try:
            mtime = os.path.getmtime(self.filename)
        except OSError:
            mtime = 0
        if self._v_program is not None and mtime == self._v_last_read:
            return
        self.pt_edit(open(self.filename), None)
        self._cook()
        if self._v_errors:
            LOG('PageTemplateFile', ERROR, 'Error in template',
                '\n'.join(self._v_errors))
            return
        self._v_last_read = mtime

    def document_src(self, REQUEST=None, RESPONSE=None):
        """Return expanded document source."""

        if RESPONSE is not None:
            RESPONSE.setHeader('Content-Type', 'text/plain')
        return self.read()

    def _get__roles__(self):
        imp = getattr(aq_parent(aq_inner(self)),
                      '%s__roles__' % self.__name__)
        if hasattr(imp, '__of__'):
            return imp.__of__(self)
        return imp

    __roles__ = ComputedAttribute(_get__roles__, 1)

    def getOwner(self, info=0):
        """Gets the owner of the executable object.

        This method is required of all objects that go into
        the security context stack.  Since this object came from the
        filesystem, it is owned by no one managed by Zope.
        """
        return None

    def __getstate__(self):
        from ZODB.POSException import StorageError
        raise StorageError, ("Instance of AntiPersistent class %s "
                             "cannot be stored." % self.__class__.__name__)
