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

from class_init import default__class_init__
from Persistence import Persistent
import Globals
from DateTime import DateTime

Persistent.__dict__['__class_init__']=default__class_init__

class PersistentUtil:

    def bobobase_modification_time(self):
        jar=self._p_jar
        oid=self._p_oid
        if jar is None or oid is None: return DateTime()

        try:
            t=self._p_mtime
            if t is None: return DateTime()
        except: t=0
        return DateTime(t)

    def locked_in_version(self):
        """Was the object modified in any version?
        """
        jar=self._p_jar
        oid=self._p_oid
        if jar is None or oid is None: return None
        try: mv=jar.modifiedInVersion
        except: pass
        else: return mv(oid)

        # BoboPOS 2 code:
        oid=self._p_oid
        return (oid
                and Globals.VersionBase.locks.has_key(oid)
                and Globals.VersionBase.verify_lock(oid)
                and 'some version')

    def modified_in_version(self):
        """Was the object modified in this version?
        """
        jar=self._p_jar
        oid=self._p_oid
        if jar is None or oid is None: return None
        try: mv=jar.modifiedInVersion
        except: pass
        else: return mv(oid)==jar.getVersion()

        # BoboPOS 2 code:
        jar=self._p_jar
        if jar is None:
            if hasattr(self,'aq_parent') and hasattr(self.aq_parent, '_p_jar'):
                jar=self.aq_parent._p_jar
            if jar is None: return 0
        if not jar.name: return 0
        try: jar.db[self._p_oid]
        except: return 0
        return 1

for k, v in PersistentUtil.__dict__.items(): Persistent.__dict__[k]=v
