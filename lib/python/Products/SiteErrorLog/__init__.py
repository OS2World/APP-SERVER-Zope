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
"""Site error log product.

$Id: __init__.py,v 1.3 2002/08/14 22:25:11 mj Exp $
"""

import SiteErrorLog

def initialize(context):
    context.registerClass(SiteErrorLog.SiteErrorLog,
                          constructors=(SiteErrorLog.manage_addErrorLog,),
                          permission=SiteErrorLog.use_error_logging,
                          icon='www/error.gif')
