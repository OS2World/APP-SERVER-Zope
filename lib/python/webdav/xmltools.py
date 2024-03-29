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

"""WebDAV XML parsing tools. Note that this module does just
   enough for the purposes of DAV - it is not intended as a
   general xml toolkit, and will probably eventually go away
   in favor of a standard xml package once some issues are
   worked out."""

__version__='$Revision: 1.13 $'[11:-2]

import sys, os
import Shared.DC.xml.xmllib
from Acquisition import Implicit


type_document=0
type_element=1
type_attribute=2
type_text=3
type_cdata=4
type_entityref=5
type_entity=6
type_procinst=7
type_comment=8
type_notation=9


class Node(Implicit):
    """Common base class for Node objects."""
    __name__=''
    __value__=''
    __attrs__=[]
    __nodes__=[]
    __nskey__=''

    def name(self):  return self.__name__
    def attrs(self): return self.__attrs__
    def value(self): return self.__value__
    def nodes(self): return self.__nodes__
    def nskey(self): return self.__nskey__

    def addNode(self, node):
        self.__nodes__.append(node.__of__(self))

    def namespace(self):
        nskey=self.__nskey__
        while 1:
            if hasattr(self, '__nsdef__'):
                val=self.__nsdef__.get(nskey, None)
                if val is not None: return val
            if not hasattr(self, 'aq_parent'):
                return ''
            self=self.aq_parent

    def elements(self, name=None, ns=None ):
        nodes=[]
        name=name and name.lower()
        for node in self.__nodes__:
            if node.__type__==type_element and \
               ((name is None) or ((node.__name__.lower())==name)) and \
               ((ns is None) or (node.namespace()==ns)):
                nodes.append(node)
        return nodes

    def __getitem__(self, n):
        return self.__nodes__[n]

    def qname(self):
        ns=self.__nskey__
        if ns: ns='%s:' % ns
        return '%s%s' % (ns, self.__name__)

    def toxml(self):
        return self.__value__

    def strval(self):
        return self.toxml()


class Document(Node):
    def __init__(self, encoding='utf-8', stdalone=''):
        self.__name__ ='document'
        self.__nodes__=[]
        self.encoding=encoding
        self.stdalone=stdalone
        self.document=self

    def toxml(self):
        result=['<?xml version="1.0" encoding="%s"?>' % self.encoding]
        for node in self.__nodes__:
            result.append(node.toxml())
        return ''.join(result)

    #def __del__(self):
    #    self.document=None
    #    print 'bye!'

class Element(Node):
    __type__=type_element

    def __init__(self, name, attrs={}):
        self.__name__ =name
        self.__attrs__=[]
        self.__nodes__=[]
        self.__nsdef__={}
        self.__nskey__=''
        for name, val in attrs.items():
            attr=Attribute(name, val)
            self.__attrs__.append(attr)
        self.ns_parse()
        parts=self.__name__.split(':')
        if len(parts) > 1:
            self.__nskey__=parts[0]
            self.__name__=':'.join(parts[1:])

    def ns_parse(self):
        nsdef=self.__nsdef__={}
        for attr in self.attrs():
            name, val=attr.name(), attr.value()
            key=name.lower()
            if key[:6]=='xmlns:':
                nsdef[name[6:]]=val
            elif key=='xmlns':
                nsdef['']=val

    def fixup(self):
        self.__attrs__=map(lambda n, s=self: n.__of__(s), self.__attrs__)

    def get_attr(self, name, ns=None, default=None):
        for attr in self.__attrs__:
            if attr.name()==name and (ns is None) or (ns==attr.namespace()):
                return attr
        return default

    def del_attr(self, name):
        attrs=[]
        for attr in self.__attrs__:
            if attr.name() != name:
                attrs.append(attr)
        self.__attrs__=attrs

    def remap(self, dict, n=0, top=1):
        # The remap method effectively rewrites an element and all of its
        # children, consolidating namespace declarations into the element
        # on which the remap function is called and fixing up namespace
        # lookup structures.
        nsval=self.namespace()
        if not nsval: nsid=''
        elif not dict.has_key(nsval):
            nsid='ns%d' % n
            dict[nsval]=nsid
            n=n+1
        else: nsid=dict[nsval]
        for attr in self.__attrs__:
            dict, n=attr.remap(dict, n, 0)
        for node in self.elements():
            dict, n=node.remap(dict, n, 0)
        attrs=[]
        for attr in self.__attrs__:
            name=attr.__name__
            if not (((len(name) >= 6) and (name[:6]=='xmlns:')) or \
                    name=='xmlns'):
                attrs.append(attr)
        self.__attrs__=attrs
        self.__nsdef__={}
        self.__nskey__=nsid
        if top:
            attrs=self.__attrs__
            keys=dict.keys()
            keys.sort()
            for key in keys:
                attr=Attribute('xmlns:%s' % dict[key], key)
                attrs.append(attr.__of__(self))
            self.__attrs__=attrs
            self.ns_parse()
        return dict, n

    def toxml(self):
        qname=self.qname()
        result=['<%s' % qname]
        for attr in self.__attrs__:
            result.append(attr.toxml())
        if not self.__value__ and not self.__nodes__:
            result.append('/>')
        else:
            result.append('>')
            for node in self.__nodes__:
                result.append(node.toxml())
            result.append('</%s>' % qname)
        return ''.join(result)

    def strval(self, top=1):
        if not self.__value__ and not self.__nodes__:
            return ''
        result=map(lambda n: n.toxml(), self.__nodes__)
        return ''.join(result)

class Attribute(Node):
    __type__=type_attribute
    def __init__(self, name, val):
        self.__name__=name
        self.__value__=val
        self.__nskey__=''
        parts=name.split(':')
        if len(parts) > 1:
            pre=parts[0].lower()
            if not (pre in ('xml', 'xmlns')):
                self.__nskey__=parts[0]
                self.__name__=':'.join(parts[1:])

    def remap(self, dict, n=0, top=1):
        nsval=self.namespace()
        if not nsval: nsid=''
        elif not dict.has_key(nsval):
            nsid='ns%d' % n
            dict[nsval]=nsid
            n=n+1
        else: nsid=dict[nsval]
        self.__nskey__=nsid
        return dict, n

    def toxml(self):
        ns=self.__nskey__
        if ns: ns='%s:' % ns
        return ' %s%s="%s"' % (ns, self.__name__, self.__value__)

class Text(Node):
    __name__='#text'
    __type__=type_text
    def __init__(self, val):
        self.__value__=val
    def toxml(self):
        return escape(self.__value__)

class CData(Node):
    __type__=type_cdata
    __name__='#cdata'
    def __init__(self, val):
        self.__value__=val
    def toxml(self):
        return '<![CDATA[%s]]>' % self.__value__

class EntityRef(Node):
    __name__='#entityref'
    __type__=type_entityref
    def __init__(self, val):
        self.__value__=val
    def toxml(self):
        return '&%s;' % self.__value__

class Entity(Node):
    __name__='#entity'
    __type__=type_entity
    def __init__(self, name, pubid, sysid, nname):
        self.__value__=val
    def toxml(self):
        return ''

class ProcInst(Node):
    __type__=type_procinst
    def __init__(self, name, val):
        self.__name__=name
        self.__value__=val
    def toxml(self):
        return '<?%s %s?>' % (self.__name__, self.__value__)

class Comment(Node):
    __name__='#comment'
    __type__=type_comment
    def __init__(self, val):
        self.__value__=val
    def toxml(self):
        return '<!--%s-->' % self.__value__





class XmlParser(Shared.DC.xml.xmllib.XMLParser):
    def __init__(self):
        Shared.DC.xml.xmllib.XMLParser.__init__(self)
        self.root=None
        self.node=None

    def parse(self, data):
        self.feed(data)
        self.close()
        return self.root

    def add(self, node):
        self.node.addNode(node)

    def push(self, node):
        self.node.addNode(node)
        self.node=self.node.__nodes__[-1]

    def pop(self):
        self.node=self.node.aq_parent

    def unknown_starttag(self, name, attrs):
        node=Element(name, attrs)
        self.push(node)
        # Fixup aq chain!
        self.node.fixup()

    def unknown_endtag(self, name):
        self.pop()

    def handle_xml(self, encoding, stdalone):
        self.root=Document(encoding, stdalone)
        self.node=self.root

    def handle_doctype(self, tag, pubid, syslit, data):
        pass

    def handle_entity(self, name, strval, pubid, syslit, ndata):
        self.add(Entity(name, strval, pubid, syslit, ndata))

    def handle_cdata(self, data):
        self.add(CData(data))

    def handle_proc(self, name, data):
        self.add(ProcInst(name, data))

    def handle_comment(self, data):
        self.add(Comment(data))

    def handle_data(self, data):
        self.add(Text(data))

    def unknown_entityref(self, data):
        self.add(EntityRef(data))



def escape(data, rmap={}):
    data=data.replace( "&", "&amp;")
    data=data.replace( "<", "&lt;")
    data=data.replace( ">", "&gt;")
    for key, val in rmap.items():
        data=data.replace( key, val)
    return data

def remap(data, dict={'DAV:': 'd'}):
    root=XmlParser().parse(data)
    root.elements()[0].remap(dict, 0)
    return root.toxml()
