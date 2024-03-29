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
__rcs_id__='$Id: MIMETag.py,v 1.10 2002/08/14 22:14:27 mj Exp $'
__version__='$Revision: 1.10 $'[11:-2]

from DocumentTemplate.DT_Util import *
from DocumentTemplate.DT_String import String
from MimeWriter import MimeWriter
from cStringIO import StringIO
import mimetools

MIMEError = "MIME Tag Error"

class MIMETag:
    '''
    '''

    name='mime'
    blockContinuations=('boundary',)
    encode=None

    def __init__(self, blocks):
        self.sections = []

        for tname, args, section in blocks:
            if tname == 'mime':
                args = parse_params( args
                                   , type=None, type_expr=None
                                   , disposition=None, disposition_expr=None
                                   , encode=None, encode_expr=None
                                   , name=None, name_expr=None
                                   , filename=None, filename_expr=None
                                   , skip_expr=None
                                   , multipart=None
                                   )
                self.multipart = args.get('multipart', 'mixed')
            else:
                args = parse_params( args
                                   , type=None, type_expr=None
                                   , disposition=None, disposition_expr=None
                                   , encode=None, encode_expr=None
                                   , name=None, name_expr=None
                                   , filename=None, filename_expr=None
                                   , skip_expr=None
                                   )

            has_key=args.has_key

            if has_key('type'):
                type = args['type']
            else:
                type = 'application/octet-stream'

            if has_key('type_expr'):
                if has_key('type'):
                    raise ParseError, _tm('type and type_expr given', 'mime')
                args['type_expr']=Eval(args['type_expr'])
            elif not has_key('type'):
                args['type']='application/octet-stream'

            if has_key('disposition_expr'):
                if has_key('disposition'):
                    raise ParseError, _tm('disposition and disposition_expr given', 'mime')
                args['disposition_expr']=Eval(args['disposition_expr'])
            elif not has_key('disposition'):
                args['disposition']=''

            if has_key('encode_expr'):
                if has_key('encode'):
                    raise ParseError, _tm('encode and encode_expr given', 'mime')
                args['encode_expr']=Eval(args['encode_expr'])
            elif not has_key('encode'):
                args['encode']='base64'

            if has_key('name_expr'):
                if has_key('name'):
                    raise ParseError, _tm('name and name_expr given', 'mime')
                args['name_expr']=Eval(args['name_expr'])
            elif not has_key('name'):
                args['name']=''

            if has_key('filename_expr'):
                if has_key('filename'):
                    raise ParseError, _tm('filename and filename_expr given', 'mime')
                args['filename_expr']=Eval(args['filename_expr'])
            elif not has_key('filename'):
                args['filename']=''

            if has_key('skip_expr'):
                args['skip_expr']=Eval(args['skip_expr'])

            if args['encode'] not in \
            ('base64', 'quoted-printable', 'uuencode', 'x-uuencode',
             'uue', 'x-uue', '7bit'):
                raise MIMEError, (
                    'An unsupported encoding was specified in tag')

            self.sections.append((args, section.blocks))


    def render(self, md):
        contents=[]
        IO = StringIO()
        IO.write("Mime-Version: 1.0\n")
        mw = MimeWriter(IO)
        outer = mw.startmultipartbody(self.multipart)
        for x in self.sections:
            a, b = x
            has_key=a.has_key

            if has_key('skip_expr') and a['skip_expr'].eval(md):
                continue

            inner = mw.nextpart()

            if has_key('type_expr'): t=a['type_expr'].eval(md)
            else: t=a['type']

            if has_key('disposition_expr'): d=a['disposition_expr'].eval(md)
            else: d=a['disposition']

            if has_key('encode_expr'): e=a['encode_expr'].eval(md)
            else: e=a['encode']

            if has_key('name_expr'): n=a['name_expr'].eval(md)
            else: n=a['name']

            if has_key('filename_expr'): f=a['filename_expr'].eval(md)
            else: f=a['filename']

            if d:
                if f:
                    inner.addheader('Content-Disposition', '%s;\n filename="%s"' % (d, f))
                else:
                    inner.addheader('Content-Disposition', d)

            inner.addheader('Content-Transfer-Encoding', e)
            if n:
                plist = [('name', n)]
            else:
                plist = []

            innerfile = inner.startbody(t, plist, 1)

            output = StringIO()
            if e == '7bit':
                innerfile.write(render_blocks(b, md))
            else:
                mimetools.encode(StringIO(render_blocks(b, md)),
                                 output, e)
                output.seek(0)
                innerfile.write(output.read())

        # XXX what if self.sections is empty ??? does it matter that mw.lastpart() is called
        # right after mw.startmultipartbody() ?
        if x is self.sections[-1]:
            mw.lastpart()

        outer.seek(0)
        return outer.read()


    __call__=render



String.commands['mime'] = MIMETag
