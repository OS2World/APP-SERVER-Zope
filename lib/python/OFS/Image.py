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
"""Image object"""

__version__='$Revision: 1.141.4.5 $'[11:-2]

import Globals, struct
from OFS.content_types import guess_content_type
from Globals import DTMLFile
from PropertyManager import PropertyManager
from AccessControl.Role import RoleManager
from webdav.common import rfc1123_date
from webdav.Lockable import ResourceLockedError
from webdav.WriteLockInterface import WriteLockInterface
from SimpleItem import Item_w__name__
from cStringIO import StringIO
from Globals import Persistent
from Acquisition import Implicit
from DateTime import DateTime
from Cache import Cacheable
from mimetools import choose_boundary
from ZPublisher import HTTPRangeSupport
from ZPublisher.HTTPRequest import FileUpload
from cgi import escape

StringType=type('')
manage_addFileForm=DTMLFile('dtml/imageAdd', globals(),Kind='File',kind='file')
def manage_addFile(self,id,file='',title='',precondition='', content_type='',
                   REQUEST=None):
    """Add a new File object.

    Creates a new File object 'id' with the contents of 'file'"""

    id=str(id)
    title=str(title)
    content_type=str(content_type)
    precondition=str(precondition)

    id, title = cookId(id, title, file)

    self=self.this()

    # First, we create the file without data:
    self._setObject(id, File(id,title,'',content_type, precondition))

    # Now we "upload" the data.  By doing this in two steps, we
    # can use a database trick to make the upload more efficient.
    if file:
        self._getOb(id).manage_upload(file)
    if content_type:
        self._getOb(id).content_type=content_type

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(self.absolute_url()+'/manage_main')


class File(Persistent, Implicit, PropertyManager,
           RoleManager, Item_w__name__, Cacheable):
    """A File object is a content object for arbitrary files."""

    __implements__ = (WriteLockInterface, HTTPRangeSupport.HTTPRangeInterface)
    meta_type='File'


    precondition=''
    size=None

    manage_editForm  =DTMLFile('dtml/fileEdit',globals(),
                               Kind='File',kind='file')
    manage_editForm._setName('manage_editForm')
    manage=manage_main=manage_editForm
    manage_uploadForm=manage_editForm

    manage_options=(
        (
        {'label':'Edit', 'action':'manage_main',
         'help':('OFSP','File_Edit.stx')},
        {'label':'View', 'action':'',
         'help':('OFSP','File_View.stx')},
        )
        + PropertyManager.manage_options
        + RoleManager.manage_options
        + Item_w__name__.manage_options
        + Cacheable.manage_options
        )


    __ac_permissions__=(
        ('View management screens',
         ('manage', 'manage_main',)),
        ('Change Images and Files',
         ('manage_edit','manage_upload','PUT')),
        ('View',
         ('index_html', 'view_image_or_file', 'get_size',
          'getContentType', '')),
        ('FTP access',
         ('manage_FTPstat','manage_FTPget','manage_FTPlist')),
        ('Delete objects',
         ('DELETE',)),
        )


    _properties=({'id':'title', 'type': 'string'},
                 {'id':'content_type', 'type':'string'},
                 )

    def __init__(self, id, title, file, content_type='', precondition=''):
        self.__name__=id
        self.title=title
        self.precondition=precondition

        data, size = self._read_data(file)
        content_type=self._get_content_type(file, data, id, content_type)
        self.update_data(data, content_type, size)

    def id(self):
        return self.__name__

    def index_html(self, REQUEST, RESPONSE):
        """
        The default view of the contents of a File or Image.

        Returns the contents of the file or image.  Also, sets the
        Content-Type HTTP header to the objects content type.
        """

        # HTTP If-Modified-Since header handling.
        header=REQUEST.get_header('If-Modified-Since', None)
        if header is not None:
            header=header.split( ';')[0]
            # Some proxies seem to send invalid date strings for this
            # header. If the date string is not valid, we ignore it
            # rather than raise an error to be generally consistent
            # with common servers such as Apache (which can usually
            # understand the screwy date string as a lucky side effect
            # of the way they parse it).
            # This happens to be what RFC2616 tells us to do in the face of an
            # invalid date.
            try:    mod_since=long(DateTime(header).timeTime())
            except: mod_since=None
            if mod_since is not None:
                if self._p_mtime:
                    last_mod = long(self._p_mtime)
                else:
                    last_mod = long(0)
                if last_mod > 0 and last_mod <= mod_since:
                    # Set header values since apache caching will return Content-Length
                    # of 0 in response if size is not set here
                    RESPONSE.setHeader('Last-Modified', rfc1123_date(self._p_mtime))
                    RESPONSE.setHeader('Content-Type', self.content_type)
                    RESPONSE.setHeader('Content-Length', self.size)
                    RESPONSE.setHeader('Accept-Ranges', 'bytes')
                    RESPONSE.setStatus(304)
                    return ''

        if self.precondition and hasattr(self,self.precondition):
            # Grab whatever precondition was defined and then
            # execute it.  The precondition will raise an exception
            # if something violates its terms.
            c=getattr(self,self.precondition)
            if hasattr(c,'isDocTemp') and c.isDocTemp:
                c(REQUEST['PARENTS'][1],REQUEST)
            else:
                c()

        # HTTP Range header handling
        range = REQUEST.get_header('Range', None)
        request_range = REQUEST.get_header('Request-Range', None)
        if request_range is not None:
            # Netscape 2 through 4 and MSIE 3 implement a draft version
            # Later on, we need to serve a different mime-type as well.
            range = request_range
        if_range = REQUEST.get_header('If-Range', None)
        if range is not None:
            ranges = HTTPRangeSupport.parseRange(range)

            if if_range is not None:
                # Only send ranges if the data isn't modified, otherwise send
                # the whole object. Support both ETags and Last-Modified dates!
                if len(if_range) > 1 and if_range[:2] == 'ts':
                    # ETag:
                    if if_range != self.http__etag():
                        # Modified, so send a normal response. We delete
                        # the ranges, which causes us to skip to the 200
                        # response.
                        ranges = None
                else:
                    # Date
                    date = if_range.split( ';')[0]
                    try: mod_since=long(DateTime(date).timeTime())
                    except: mod_since=None
                    if mod_since is not None:
                        if self._p_mtime:
                            last_mod = long(self._p_mtime)
                        else:
                            last_mod = long(0)
                        if last_mod > mod_since:
                            # Modified, so send a normal response. We delete
                            # the ranges, which causes us to skip to the 200
                            # response.
                            ranges = None

            if ranges:
                # Search for satisfiable ranges.
                satisfiable = 0
                for start, end in ranges:
                    if start < self.size:
                        satisfiable = 1
                        break

                if not satisfiable:
                    RESPONSE.setHeader('Content-Range',
                        'bytes */%d' % self.size)
                    RESPONSE.setHeader('Accept-Ranges', 'bytes')
                    RESPONSE.setHeader('Last-Modified',
                        rfc1123_date(self._p_mtime))
                    RESPONSE.setHeader('Content-Type', self.content_type)
                    RESPONSE.setHeader('Content-Length', self.size)
                    RESPONSE.setStatus(416)
                    return ''

                ranges = HTTPRangeSupport.expandRanges(ranges, self.size)
                                
                if len(ranges) == 1:
                    # Easy case, set extra header and return partial set.
                    start, end = ranges[0]
                    size = end - start

                    RESPONSE.setHeader('Last-Modified',
                        rfc1123_date(self._p_mtime))
                    RESPONSE.setHeader('Content-Type', self.content_type)
                    RESPONSE.setHeader('Content-Length', size)
                    RESPONSE.setHeader('Accept-Ranges', 'bytes')
                    RESPONSE.setHeader('Content-Range',
                        'bytes %d-%d/%d' % (start, end - 1, self.size))
                    RESPONSE.setStatus(206) # Partial content

                    data = self.data
                    if type(data) is StringType:
                        return data[start:end]

                    # Linked Pdata objects. Urgh.
                    pos = 0
                    while data is not None:
                        l = len(data.data)
                        pos = pos + l
                        if pos > start:
                            # We are within the range
                            lstart = l - (pos - start)

                            if lstart < 0: lstart = 0

                            # find the endpoint
                            if end <= pos:
                                lend = l - (pos - end)

                                # Send and end transmission
                                RESPONSE.write(data[lstart:lend])
                                break

                            # Not yet at the end, transmit what we have.
                            RESPONSE.write(data[lstart:])

                        data = data.next

                    return ''

                else:
                    boundary = choose_boundary()

                    # Calculate the content length
                    size = (8 + len(boundary) + # End marker length
                        len(ranges) * (         # Constant lenght per set
                            49 + len(boundary) + len(self.content_type) +
                            len('%d' % self.size)))
                    for start, end in ranges:
                        # Variable length per set
                        size = (size + len('%d%d' % (start, end - 1)) +
                            end - start)


                    # Some clients implement an earlier draft of the spec, they
                    # will only accept x-byteranges.
                    draftprefix = (request_range is not None) and 'x-' or ''

                    RESPONSE.setHeader('Content-Length', size)
                    RESPONSE.setHeader('Accept-Ranges', 'bytes')
                    RESPONSE.setHeader('Last-Modified',
                        rfc1123_date(self._p_mtime))
                    RESPONSE.setHeader('Content-Type',
                        'multipart/%sbyteranges; boundary=%s' % (
                            draftprefix, boundary))
                    RESPONSE.setStatus(206) # Partial content

                    data = self.data
                    # The Pdata map allows us to jump into the Pdata chain
                    # arbitrarily during out-of-order range searching.
                    pdata_map = {}
                    pdata_map[0] = data

                    for start, end in ranges:
                        RESPONSE.write('\r\n--%s\r\n' % boundary)
                        RESPONSE.write('Content-Type: %s\r\n' %
                            self.content_type)
                        RESPONSE.write(
                            'Content-Range: bytes %d-%d/%d\r\n\r\n' % (
                                start, end - 1, self.size))

                        if type(data) is StringType:
                            RESPONSE.write(data[start:end])

                        else:
                            # Yippee. Linked Pdata objects. The following
                            # calculations allow us to fast-forward through the
                            # Pdata chain without a lot of dereferencing if we
                            # did the work already.
                            first_size = len(pdata_map[0].data)
                            if start < first_size:
                                closest_pos = 0
                            else:
                                closest_pos = (
                                    ((start - first_size) >> 16 << 16) +
                                    first_size)
                            pos = min(closest_pos, max(pdata_map.keys()))
                            data = pdata_map[pos]

                            while data is not None:
                                l = len(data.data)
                                pos = pos + l
                                if pos > start:
                                    # We are within the range
                                    lstart = l - (pos - start)

                                    if lstart < 0: lstart = 0

                                    # find the endpoint
                                    if end <= pos:
                                        lend = l - (pos - end)

                                        # Send and loop to next range
                                        RESPONSE.write(data[lstart:lend])
                                        break

                                    # Not yet at the end, transmit what we have.
                                    RESPONSE.write(data[lstart:])

                                data = data.next
                                # Store a reference to a Pdata chain link so we
                                # don't have to deref during this request again.
                                pdata_map[pos] = data

                    # Do not keep the link references around.
                    del pdata_map

                    RESPONSE.write('\r\n--%s--\r\n' % boundary)
                    return ''

        RESPONSE.setHeader('Last-Modified', rfc1123_date(self._p_mtime))
        RESPONSE.setHeader('Content-Type', self.content_type)
        RESPONSE.setHeader('Content-Length', self.size)
        RESPONSE.setHeader('Accept-Ranges', 'bytes')

        # Don't cache the data itself, but provide an opportunity
        # for a cache manager to set response headers.
        self.ZCacheable_set(None)

        data=self.data
        if type(data) is type(''): 
            RESPONSE.setBase(None)
            return data

        while data is not None:
            RESPONSE.write(data.data)
            data=data.next

        return ''

    def view_image_or_file(self, URL1):
        """
        The default view of the contents of the File or Image.
        """
        raise 'Redirect', URL1

    # private
    update_data__roles__=()
    def update_data(self, data, content_type=None, size=None):
        if content_type is not None: self.content_type=content_type
        if size is None: size=len(data)
        self.size=size
        self.data=data
        self.ZCacheable_invalidate()
        self.http__refreshEtag()

    def manage_edit(self, title, content_type, precondition='',
                    filedata=None, REQUEST=None):
        """
        Changes the title and content type attributes of the File or Image.
        """
        if self.wl_isLocked():
            raise ResourceLockedError, "File is locked via WebDAV"

        self.title=str(title)
        self.content_type=str(content_type)
        if precondition: self.precondition=str(precondition)
        elif self.precondition: del self.precondition
        if filedata is not None:
            self.update_data(filedata, content_type, len(filedata))
        else:
            self.ZCacheable_invalidate()
        if REQUEST:
            message="Saved changes."
            return self.manage_main(self,REQUEST,manage_tabs_message=message)

    def manage_upload(self,file='',REQUEST=None):
        """
        Replaces the current contents of the File or Image object with file.

        The file or images contents are replaced with the contents of 'file'.
        """
        if self.wl_isLocked():
            raise ResourceLockedError, "File is locked via WebDAV"

        data, size = self._read_data(file)
        content_type=self._get_content_type(file, data, self.__name__,
                                            'application/octet-stream')
        self.update_data(data, content_type, size)

        if REQUEST:
            message="Saved changes."
            return self.manage_main(self,REQUEST,manage_tabs_message=message)

    def _get_content_type(self, file, body, id, content_type=None):
        headers=getattr(file, 'headers', None)
        if headers and headers.has_key('content-type'):
            content_type=headers['content-type']
        else:
            if type(body) is not type(''): body=body.data
            content_type, enc=guess_content_type(
                getattr(file, 'filename',id), body, content_type)
        return content_type

    def _read_data(self, file):

        n=1 << 16

        if type(file) is StringType:
            size=len(file)
            if size < n: return file, size
            return Pdata(file), size
        elif isinstance(file, FileUpload) and not file:
            raise ValueError, 'File not specified'

        if hasattr(file, '__class__') and file.__class__ is Pdata:
            size=len(file)
            return file, size

        seek=file.seek
        read=file.read

        seek(0,2)
        size=end=file.tell()

        if size <= 2*n:
            seek(0)
            if size < n: return read(size), size
            return Pdata(read(size)), size

        # Make sure we have an _p_jar, even if we are a new object, by
        # doing a sub-transaction commit.
        get_transaction().commit(1)

        jar=self._p_jar

        if jar is None:
            # Ugh
            seek(0)
            return Pdata(read(size)), size

        # Now we're going to build a linked list from back
        # to front to minimize the number of database updates
        # and to allow us to get things out of memory as soon as
        # possible.
        next=None
        while end > 0:
            pos=end-n
            if pos < n: pos=0 # we always want at least n bytes
            seek(pos)
            data=Pdata(read(end-pos))

            # Woooop Woooop Woooop! This is a trick.
            # We stuff the data directly into our jar to reduce the
            # number of updates necessary.
            data._p_jar=jar

            # This is needed and has side benefit of getting
            # the thing registered:
            data.next=next

            # Now make it get saved in a sub-transaction!
            get_transaction().commit(1)

            # Now make it a ghost to free the memory.  We
            # don't need it anymore!
            data._p_changed=None

            next=data
            end=pos

        return next, size

    def PUT(self, REQUEST, RESPONSE):
        """Handle HTTP PUT requests"""
        self.dav__init(REQUEST, RESPONSE)
        self.dav__simpleifhandler(REQUEST, RESPONSE, refresh=1)
        type=REQUEST.get_header('content-type', None)

        file=REQUEST['BODYFILE']

        data, size = self._read_data(file)
        content_type=self._get_content_type(file, data, self.__name__,
                                            type or self.content_type)
        self.update_data(data, content_type, size)

        RESPONSE.setStatus(204)
        return RESPONSE

    def get_size(self):
        """Get the size of a file or image.

        Returns the size of the file or image.
        """
        size=self.size
        if size is None: size=len(self.data)
        return size

    # deprecated; use get_size!
    getSize=get_size

    def getContentType(self):
        """Get the content type of a file or image.

        Returns the content type (MIME type) of a file or image.
        """
        return self.content_type


    def __str__(self): return str(self.data)
    def __len__(self): return 1

    manage_FTPget=index_html


manage_addImageForm=DTMLFile('dtml/imageAdd',globals(),
                             Kind='Image',kind='image')
def manage_addImage(self, id, file, title='', precondition='', content_type='',
                    REQUEST=None):
    """
    Add a new Image object.

    Creates a new Image object 'id' with the contents of 'file'.
    """

    id=str(id)
    title=str(title)
    content_type=str(content_type)
    precondition=str(precondition)

    id, title = cookId(id, title, file)

    self=self.this()

    # First, we create the image without data:
    self._setObject(id, Image(id,title,'',content_type, precondition))

    # Now we "upload" the data.  By doing this in two steps, we
    # can use a database trick to make the upload more efficient.
    if file:
        self._getOb(id).manage_upload(file)
    if content_type:
        self._getOb(id).content_type=content_type

    if REQUEST is not None:
        try:    url=self.DestinationURL()
        except: url=REQUEST['URL1']
        REQUEST.RESPONSE.redirect('%s/manage_main' % url)
    return id


def getImageInfo(data):
    data = str(data)
    size = len(data)
    height = -1
    width = -1
    content_type = ''

    # handle GIFs
    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # Check to see if content_type is correct
        content_type = 'image/gif'
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)

    # See PNG v1.2 spec (http://www.cdrom.com/pub/png/spec/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif ((size >= 24) and (data[:8] == '\211PNG\r\n\032\n')
          and (data[12:16] == 'IHDR')):
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif (size >= 16) and (data[:8] == '\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[8:16])
        width = int(w)
        height = int(h)

    # handle JPEGs
    elif (size >= 2) and (data[:2] == '\377\330'):
        content_type = 'image/jpeg'
        jpeg = StringIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = jpeg.read(1)
                while (ord(b) == 0xFF): b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack(">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0])-2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except: pass

    return content_type, width, height


class Image(File):
    """Image objects can be GIF, PNG or JPEG and have the same methods
    as File objects.  Images also have a string representation that
    renders an HTML 'IMG' tag.
    """
    __implements__ = (WriteLockInterface,)
    meta_type='Image'


    height=''
    width=''

    __ac_permissions__=(
        ('View management screens',
         ('manage', 'manage_main',)),
        ('Change Images and Files',
         ('manage_edit','manage_upload','PUT')),
        ('View',
         ('index_html', 'tag', 'view_image_or_file', 'get_size',
          'getContentType', '')),
        ('FTP access',
         ('manage_FTPstat','manage_FTPget','manage_FTPlist')),
        ('Delete objects',
         ('DELETE',)),
        )

    _properties=({'id':'title', 'type': 'string'},
                 {'id':'content_type', 'type':'string','mode':'w'},
                 {'id':'height', 'type':'string'},
                 {'id':'width', 'type':'string'},
                 )

    manage_options=(
        ({'label':'Edit', 'action':'manage_main',
         'help':('OFSP','Image_Edit.stx')},
         {'label':'View', 'action':'view_image_or_file',
         'help':('OFSP','Image_View.stx')},)
        + PropertyManager.manage_options
        + RoleManager.manage_options
        + Item_w__name__.manage_options
        + Cacheable.manage_options
        )

    manage_editForm  =DTMLFile('dtml/imageEdit',globals(),
                               Kind='Image',kind='image')
    view_image_or_file =DTMLFile('dtml/imageView',globals())
    manage_editForm._setName('manage_editForm')
    manage=manage_main=manage_editForm
    manage_uploadForm=manage_editForm

    # private
    update_data__roles__=()
    def update_data(self, data, content_type=None, size=None):
        if size is None: size=len(data)

        self.size=size
        self.data=data

        ct, width, height = getImageInfo(data)
        if ct:
            content_type = ct
        if width >= 0 and height >= 0:
            self.width = width
            self.height = height

        # Now we should have the correct content type, or still None
        if content_type is not None: self.content_type = content_type

        self.ZCacheable_invalidate()


    def __str__(self):
        return self.tag()

    def tag(self, height=None, width=None, alt=None,
            scale=0, xscale=0, yscale=0, css_class=None, title=None, **args):
        """
        Generate an HTML IMG tag for this image, with customization.
        Arguments to self.tag() can be any valid attributes of an IMG tag.
        'src' will always be an absolute pathname, to prevent redundant
        downloading of images. Defaults are applied intelligently for
        'height', 'width', and 'alt'. If specified, the 'scale', 'xscale',
        and 'yscale' keyword arguments will be used to automatically adjust
        the output height and width values of the image tag.

        Since 'class' is a Python reserved word, it cannot be passed in
        directly in keyword arguments which is a problem if you are
        trying to use 'tag()' to include a CSS class. The tag() method
        will accept a 'css_class' argument that will be converted to
        'class' in the output tag to work around this.
        """
        if height is None: height=self.height
        if width is None:  width=self.width

        # Auto-scaling support
        xdelta = xscale or scale
        ydelta = yscale or scale

        if xdelta and width:
            width =  str(int(round(int(width) * xdelta)))
        if ydelta and height:
            height = str(int(round(int(height) * ydelta)))

        result='<img src="%s"' % (self.absolute_url())

        if alt is None:
            alt=getattr(self, 'title', '')
        result = '%s alt="%s"' % (result, escape(alt, 1))

        if title is None:
            title=getattr(self, 'title', '')
        result = '%s title="%s"' % (result, escape(title, 1))

        if height:
            result = '%s height="%s"' % (result, height)

        if width:
            result = '%s width="%s"' % (result, width)

        if not 'border' in [ x.lower() for x in  args.keys()]:
            result = '%s border="0"' % result

        if css_class is not None:
            result = '%s class="%s"' % (result, css_class)

        for key in args.keys():
            value = args.get(key)
            result = '%s %s="%s"' % (result, key, value)

        return '%s />' % result


def cookId(id, title, file):
    if not id and hasattr(file,'filename'):
        filename=file.filename
        title=title or filename
        id=filename[max(filename.rfind('/'),
                        filename.rfind('\\'),
                        filename.rfind(':'),
                        )+1:]
    return id, title

class Pdata(Persistent, Implicit):
    # Wrapper for possibly large data

    next=None

    def __init__(self, data):
        self.data=data

    def __getslice__(self, i, j):
        return self.data[i:j]

    def __len__(self):
        data = str(self)
        return len(data)

    def __str__(self):
        next=self.next
        if next is None: return self.data

        r=[self.data]
        while next is not None:
            self=next
            r.append(self.data)
            next=self.next

        return ''.join(r)
