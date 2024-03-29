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

"""Commonly used utility functions."""

__version__='$Revision: 1.16.2.1 $'[11:-2]

import sys, os, time


# These are needed because the various date formats below must
# be in english per the RFCs. That means we can't use strftime,
# which is affected by different locale settings.
weekday_abbr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
weekday_full = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday']
monthname    = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def iso8601_date(ts=None):
    # Return an ISO 8601 formatted date string, required
    # for certain DAV properties.
    # '2000-11-10T16:21:09-08:00
    if ts is None: ts=time.time()
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))

def rfc850_date(ts=None):
    # Return an HTTP-date formatted date string.
    # 'Friday, 10-Nov-00 16:21:09 GMT'
    if ts is None: ts=time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(ts)
    return "%s, %02d-%3s-%2s %02d:%02d:%02d GMT" % (
            weekday_full[wd],
            day, monthname[month],
            str(year)[2:],
            hh, mm, ss)

def rfc1123_date(ts=None):
    # Return an RFC 1123 format date string, required for
    # use in HTTP Date headers per the HTTP 1.1 spec.
    # 'Fri, 10 Nov 2000 16:21:09 GMT'
    if ts is None: ts=time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(ts)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (weekday_abbr[wd],
                                                    day, monthname[month],
                                                    year,
                                                    hh, mm, ss)

def absattr(attr, c=callable):
    # Return the absolute value of an attribute,
    # calling the attr if it is callable.
    if c(attr):
        return attr()
    return attr

def aq_base(ob, getattr=getattr):
    # Return the aq_base of an object.
    return getattr(ob, 'aq_base', ob)

def is_acquired(ob, hasattr=hasattr, aq_base=aq_base, absattr=absattr):
    # Return true if this object is not considered to be
    # a direct subobject of its acquisition parent
    # Used to prevent acquisition side-affects in FTP traversal
    # Note that this method is misnamed since parents can (and do)
    # spoof it. It is not a true measure of whether something is
    # acquired, it relies on the parent's parent-ness exclusively
    if not hasattr(ob, 'aq_parent'):
        # We can't be acquired if we don't have an aq_parent
        return 0

    parent = aq_base(ob.aq_parent)
    absId  = absattr(ob.id)

    if hasattr(parent, absId):
        # Consider direct attributes not acquired
        return 0

    if hasattr(parent, '__getitem__'):
        # Use __getitem__ as opposed to has_key to avoid TTW namespace
        # issues, and to support the most minimal mapping objects
        try:
            # We assume that getitem will not acquire which
            # is the standard behavior for Zope objects
            if aq_base(ob.aq_parent[absId]) is aq_base(ob):
                # This object is an item of the aq_parent, its not acquired
                return 0
        except KeyError:
            pass

    if hasattr(parent,'_objects'):
        # XXX This is really icky
        # This ugly mess is for ZClass methods I think
        if absId+' ' in parent.objectIds():
            return 0

    if hasattr(aq_base(ob), 'isTopLevelPrincipiaApplicationObject') and \
            ob.isTopLevelPrincipiaApplicationObject:
        # This object the top level
        return 0
    return 1 # This object is acquired by our measure


def package_home(globals_dict):
    __name__=globals_dict['__name__']
    m=sys.modules[__name__]
    if hasattr(m,'__path__'):
        r=m.__path__[0]
    elif "." in __name__:
        r=sys.modules[__name__[:__name__.rfind('.')]].__path__[0]
    else:
        r=__name__
    return os.path.join(os.getcwd(), r)


def attrget(o,name,default):
    if hasattr(o,name): return getattr(o,name)
    return default

def Dictionary(**kw): return kw # Sorry Guido

try:
    # Python 2.2. already has a realpath function, while 2.1 doesn't
    realpath = os.path.realpath
except:
    if os.name == 'posix':
        def realpath(filename):
            """
            Return the canonical path of the specified filename,
            eliminating any symbolic links encountered in the path
            (this is ripped off from Python 2.2).
            """
            filename = os.path.abspath(filename)

            bits = ['/'] + filename.split('/')[1:]
            for i in range(2, len(bits)+1):
                component = os.path.join(*bits[0:i])
                if os.path.islink(component):
                    resolved = os.readlink(component)
                    (dir, file) = os.path.split(component)
                    resolved = os.path.normpath(os.path.join(dir, resolved))
                    newpath = os.path.join(*([resolved] + bits[i:]))
                    return realpath(newpath)

            return filename
    else:
        # other platforms are assumed to not have symlinks, so we alias
        # realpath to abspath
        realpath = os.path.abspath
