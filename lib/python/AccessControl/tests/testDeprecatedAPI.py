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
"""Tests for the DeprecationWarning thrown by accessing hasRole

To be removed together with the API in due time.

"""

__rcs_id__='$Id: testDeprecatedAPI.py,v 1.4 2002/08/14 21:28:08 mj Exp $'
__version__='$Revision: 1.4 $'[11:-2]

import ZODB # Sigh. Persistent needs to be set, so we import ZODB.
from AccessControl import User
import unittest, warnings

class DeprecatedAPI(unittest.TestCase):
    def setUp(self):
        # We test for warnings by turning them into exceptions
        warnings.filterwarnings('error', category=DeprecationWarning,
            module='AccessControl')

    def testDeprecatedHasRole(self):
        """hasRole has been deprecated, we expect a warning."""
        try:
            self.userObject.hasRole(None)
        except DeprecationWarning:
            pass
        else:
            self.fail('Expected DeprecationWarning, none given')

    def testAllowed(self):
        """hasRole is an alias for allowed, which should be unaffected."""
        try:
            self.userObject.allowed(None)
        except DeprecationWarning:
            self.fail('Unexpected DeprecationWarning, '
                'no warnings expected here')
        else:
            pass

    def tearDown(self):
        warnings.resetwarnings()

class BasicUser(DeprecatedAPI):
    userObject = User.SimpleUser('JoeBloke', '123', [], [])

class UnrestrictedUser(DeprecatedAPI):
    userObject = User.UnrestrictedUser('Special', '123', [], [])

class NullUnrestrictedUser(DeprecatedAPI):
    userObject = User.NullUnrestrictedUser()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BasicUser))
    suite.addTest(unittest.makeSuite(UnrestrictedUser))
    suite.addTest(unittest.makeSuite(NullUnrestrictedUser))
    return suite
