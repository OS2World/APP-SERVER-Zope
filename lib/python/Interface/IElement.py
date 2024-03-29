##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""

Revision information:
$Id: IElement.py,v 1.5 2002/08/14 21:35:32 mj Exp $
"""

from _Interface import Interface
from Attribute import Attribute

class IElement(Interface):
    """Objects that have basic documentation and tagged values.
    """

    __name__ = Attribute('__name__', 'The object name')
    __doc__  = Attribute('__doc__', 'The object doc string')

    def getName():
        """Returns the name of the object."""

    def getDoc():
        """Returns the documentation for the object."""

    def getTaggedValue(tag):
        """Returns the value associated with 'tag'."""

    def getTaggedValueTags():
        """Returns a list of all tags."""

    def setTaggedValue(tag, value):
        """Associates 'value' with 'key'."""
