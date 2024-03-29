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
"""Product objects
"""
# The new Product model:
#
#   Products may be defined in the Products folder or by placing directories
#   in lib/python/Products.
#
#   Products in lib/python/Products may have up to three sources of information:
#
#       - Static information defined via Python.  This information is
#         described and made available via __init__.py.
#
#       - Dynamic object data that gets copied into the Bobobase.
#         This is contained in product.dat (which is obfuscated).
#
#       - Static extensions supporting the dynamic data.  These too
#         are obfuscated.
#
#   Products may be copied and pasted only within the products folder.
#
#   If a product is deleted (or cut), it is automatically recreated
#   on restart if there is still a product directory.


import Globals, OFS.Folder, OFS.SimpleItem, os,  Acquisition, Products
import re, zlib, Globals, cPickle, marshal, rotor
import ZClasses, ZClasses.ZClass, AccessControl.Owned
from urllib import quote
from cgi import escape

from OFS.Folder import Folder
from Factory import Factory
from Permission import PermissionManager
import ZClasses, ZClasses.ZClass
from HelpSys.HelpSys import ProductHelp
import RefreshFuncs
from AccessControl import Unauthorized


class ProductFolder(Folder):
    "Manage a collection of Products"

    id        ='Products'
    name=title='Product Management'
    meta_type ='Product Management'
    icon='p_/ProductFolder_icon'

    all_meta_types={'name': 'Product', 'action': 'manage_addProductForm'},
    meta_types=all_meta_types

    # This prevents subobjects from being owned!
    _owner=AccessControl.Owned.UnownableOwner

    def _product(self, name): return getattr(self, name)

    manage_addProductForm=Globals.DTMLFile('dtml/addProduct',globals())
    def manage_addProduct(self, id, title, REQUEST=None):
        ' '
        i=Product(id, title)
        self._setObject(id,i)
        if REQUEST is not None:
            return self.manage_main(self,REQUEST,update_menu=1)

    def _canCopy(self, op=0):
        return 0

class Product(Folder, PermissionManager):
    """Model a product that can be created through the web.
    """
    meta_type='Product'
    icon='p_/Product_icon'
    version=''
    configurable_objects_=()
    redistributable=0
    import_error_=None
    _isBeingUsedAsAMethod_=1

    def new_version(self,
                    _intending=re.compile(r"[0-9]+").search, #TS
                    ):
        # Return a new version number based on the existing version.
        v=str(self.version)
        if not v: return '1.0'
        match = _intending(v)
        if match is None:
            return v
        while 1:
            # Find the last set of digits.
            m = _intending(v, match.end())
            if m is None:
                break
            else:
                match = m
        start = match.start()
        end = match.end()
        return v[:start] + str(1 + int(v[start:end])) + v[end:]


    meta_types=(
        ZClasses.meta_types+PermissionManager.meta_types+
        (
            {
                'name': Factory.meta_type,
                'action': 'manage_addPrincipiaFactoryForm'
                },
            )
        )

    manage_addZClassForm=ZClasses.methods['manage_addZClassForm']
    manage_addZClass    =ZClasses.methods['manage_addZClass']
    manage_subclassableClassNames=ZClasses.methods[
        'manage_subclassableClassNames']

    manage_options=(
        (Folder.manage_options[0],) +
        tuple(Folder.manage_options[2:]) +
        (
        {'label':'Distribution', 'action':'manage_distributionView',
         'help':('OFSP','Product_Distribution.stx')},
        )
        )

    manage_distributionView=Globals.DTMLFile(
        'dtml/distributionView',globals())

    _properties=Folder._properties+(
        {'id':'version', 'type': 'string'},
        )

    _reserved_names=('Help',)

    manage_addPrincipiaFactoryForm=Globals.DTMLFile(
        'dtml/addFactory',globals())
    def manage_addPrincipiaFactory(
        self, id, title, object_type, initial, permission=None, REQUEST=None):
        ' '
        i=Factory(id, title, object_type, initial, permission)
        self._setObject(id,i)
        factory = self._getOb(id)
        factory.initializePermission()
        if REQUEST is not None:
            return self.manage_main(self,REQUEST,update_menu=1)

    def __init__(self, id, title):
        self.id=id
        self.title=title

        # Workaround for unknown problem with help system and PluginIndexes product
        # NEEDS to be fixed for 2.4 ! (ajung)

        try:
            self._setObject('Help', ProductHelp('Help', id))
        except:
            pass

    def Destination(self):
        "Return the destination for factory output"
        return self
    Destination__roles__=None

    def DestinationURL(self):
        "Return the URL for the destination for factory output"
        return self.REQUEST['BASE4']
    DestinationURL__roles__=None

    def manage_distribute(self, version, RESPONSE, configurable_objects=[],
                          redistributable=0):
        "Set the product up to create a distribution and give a link"
        if self.__dict__.has_key('manage_options'):
            raise TypeError, 'This product is <b>not</b> redistributable.'
        self.version=version=version.strip()
        self.configurable_objects_=configurable_objects
        self.redistributable=redistributable
        RESPONSE.redirect('Distributions/%s-%s.tar.gz' %
                          (quote(self.id), quote(version)))

    def _distribution(self):
        # Return a distribution
        if self.__dict__.has_key('manage_options'):
            raise TypeError, 'This product is <b>not</b> redistributable.'

        id=self.id

        import tar
        rot=rotor.newrotor(id+' shshsh')
        ar=tar.tgzarchive("%s-%s" % (id, self.version))
        prefix="Products/%s/" % self.id

        # __init__.py
        ar.add(prefix+"__init__.py",
               '''"Product %s"
               ''' % id
               )

        # Extensions
        pp=id+'.'
        lpp=len(pp)
        ed=os.path.join(INSTANCE_HOME,'Extensions')
        if os.path.exists(ed):
            for name in os.listdir(ed):
                suffix=''
                if name[:lpp]==pp:
                    path=os.path.join(ed, name)
                    try:
                        f=open(path)
                        data=f.read()
                        f.close()
                        if name[-3:]=='.py':
                            data=rot.encrypt(zlib.compress(data))
                            suffix='p'
                    except: data=None
                    if data:
                        ar.add("%sExtensions/%s%s" %
                               (prefix,name[lpp:],suffix),
                               data)

        # version.txt
        ar.add(prefix+'version.txt', self.version)

        # product.dat
        f=CompressedOutputFile(rot)
        if self.redistributable:
            # Since it's redistributable, make all objects configurable.
            objectList = self._objects
        else:
            objectList = tuple(filter(
                lambda o, obs=self.configurable_objects_:
                o['id'] in obs,
                self._objects))
        meta={
            '_objects': objectList,
            'redistributable': self.redistributable,
            }
        f.write(cPickle.dumps(meta,1))

        self._p_jar.exportFile(self._p_oid, f)
        ar.add(prefix+'product.dat', f.getdata())

        ar.finish()
        return str(ar)

    class Distributions(Acquisition.Explicit):
        "Product Distributions"

        def __bobo_traverse__(self, REQUEST, name):
            if name[-7:] != '.tar.gz': raise 'Invalid Name', escape(name)
            l=name.find('-')
            id, version = name[:l], name[l+1:-7]
            product=self.aq_parent
            if product.id==id and product.version==version:
                return Distribution(product)

            raise 'Invalid version or product id', escape(name)

    Distributions=Distributions()

    manage_traceback=Globals.DTMLFile('dtml/traceback',globals())
    manage_readme=Globals.DTMLFile('dtml/readme',globals())
    def manage_get_product_readme__(self):
        for name in ('README.txt', 'README.TXT', 'readme.txt'):
            path = os.path.join(self.home, name)
            if os.path.isfile(path):
                return open(path).read()
        return ''

    def permissionMappingPossibleValues(self):
        return self.possible_permissions()

    def zclass_product_name(self):
        return self.id

    def getProductHelp(self):
        """
        Returns the ProductHelp object associated
        with the Product.
        """
        if not hasattr(self, 'Help'):
            self._setObject('Help', ProductHelp('Help', self.id))
        return self.Help

    #
    # Product refresh
    #

    _refresh_dtml = Globals.DTMLFile('dtml/refresh', globals())

    def _readRefreshTxt(self, pid=None):
        refresh_txt = None
        if pid is None:
            pid = self.id
        for productDir in Products.__path__:
            found = 0
            for name in ('refresh.txt', 'REFRESH.txt', 'REFRESH.TXT'):
                p = os.path.join(productDir, pid, name)
                if os.path.exists(p):
                    found = 1
                    break
            if found:
                try:
                    file = open(p)
                    text = file.read()
                    file.close()
                    refresh_txt = text
                    break
                except:
                    # Not found here.
                    pass
        return refresh_txt

    def manage_refresh(self, REQUEST, manage_tabs_message=None):
        '''
        Displays the refresh management screen.
        '''
        error_type = error_value = error_tb = None
        exc = RefreshFuncs.getLastRefreshException(self.id)
        if exc is not None:
            error_type, error_value, error_tb = exc
            exc = None

        refresh_txt = self._readRefreshTxt()

        # Read the persistent refresh information.
        auto = RefreshFuncs.isAutoRefreshEnabled(self._p_jar, self.id)
        deps = RefreshFuncs.getDependentProducts(self._p_jar, self.id)

        # List all product modules.
        mods = RefreshFuncs.listRefreshableModules(self.id)
        loaded_modules = []
        prefix = 'Products.%s' % self.id
        prefixdot = prefix + '.'
        lpdot = len(prefixdot)
        for name, module in mods:
            if name == prefix or name[:lpdot] == prefixdot:
                name = name[lpdot:]
                if not name:
                    name = '__init__'
            loaded_modules.append(name)

        all_auto = RefreshFuncs.listAutoRefreshableProducts(self._p_jar)
        for pid in all_auto:
            # Ignore products that don't have a refresh.txt.
            if self._readRefreshTxt(pid) is None:
                all_auto.remove(pid)
        auto_other = filter(lambda productId, myId=self.id:
                            productId != myId, all_auto)

        # Return rendered DTML.
        return self._refresh_dtml(REQUEST,
                                  id=self.id,
                                  refresh_txt=refresh_txt,
                                  error_type=error_type,
                                  error_value=error_value,
                                  error_tb=error_tb,
                                  devel_mode=Globals.DevelopmentMode,
                                  auto_refresh_enabled=auto,
                                  auto_refresh_other=auto_other,
                                  dependent_products=deps,
                                  loaded_modules=loaded_modules,
                                  manage_tabs_message=manage_tabs_message,
                                  management_view='Refresh')

    def manage_performRefresh(self, REQUEST=None):
        '''
        Attempts to perform a refresh operation.
        '''
        if self._readRefreshTxt() is None:
            raise Unauthorized, 'refresh.txt not found'
        message = None
        if RefreshFuncs.performFullRefresh(self._p_jar, self.id):
            from ZODB import Connection
            Connection.updateCodeTimestamp() # Clears cache in next connection.
            message = 'Product refreshed.'
        else:
            message = 'An exception occurred.'
        if REQUEST is not None:
            return self.manage_refresh(REQUEST, manage_tabs_message=message)

    def manage_enableAutoRefresh(self, enable=0, REQUEST=None):
        '''
        Changes the auto refresh flag for this product.
        '''
        if self._readRefreshTxt() is None:
            raise Unauthorized, 'refresh.txt not created'
        RefreshFuncs.enableAutoRefresh(self._p_jar, self.id, enable)
        if enable:
            message = 'Enabled auto refresh.'
        else:
            message = 'Disabled auto refresh.'
        if REQUEST is not None:
            return self.manage_refresh(REQUEST, manage_tabs_message=message)

    def manage_selectDependentProducts(self, selections=(), REQUEST=None):
        '''
        Selects which products to refresh simultaneously.
        '''
        if self._readRefreshTxt() is None:
            raise Unauthorized, 'refresh.txt not created'
        RefreshFuncs.setDependentProducts(self._p_jar, self.id, selections)
        if REQUEST is not None:
            return self.manage_refresh(REQUEST)



class CompressedOutputFile:
    def __init__(self, rot):
        self._c=zlib.compressobj()
        self._r=[]
        self._rot=rot
        rot.encrypt('')

    def write(self, s):
        self._r.append(self._rot.encryptmore(self._c.compress(s)))

    def getdata(self):
        self._r.append(self._rot.encryptmore(self._c.flush()))
        return ''.join(self._r)

class CompressedInputFile:
    _done=0
    def __init__(self, f, rot):
        self._c=zlib.decompressobj()
        self._b=''
        if type(rot) is type(''): rot=rotor.newrotor(rot)
        self._rot=rot
        rot.decrypt('')
        self._f=f

    def _next(self):
        if self._done: return
        l=self._f.read(8196)
        if not l:
            l=self._c.flush()
            self._done=1
        else:
            l=self._c.decompress(self._rot.decryptmore(l))
        self._b=self._b+l

    def read(self, l=None):
        if l is None:
            while not self._done: self._next()
            l=len(self._b)
        else:
            while l > len(self._b) and not self._done: self._next()
        r=self._b[:l]
        self._b=self._b[l:]

        return r

    def readline(self):
        l=self._b.find('\n')
        while l < 0 and not self._done:
            self._next()
            l=self._b.find('\n')
        if l < 0: l=len(self._b)
        else: l=l+1
        r=self._b[:l]
        self._b=self._b[l:]
        return r

class Distribution:
    "A distribution builder"

    def __init__(self, product):
        self._product=product

    def index_html(self, RESPONSE):
        "Return distribution data"
        r=self._product._distribution()
        RESPONSE['content-type']='application/x-gzip'
        return r

def initializeProduct(productp, name, home, app):
    # Initialize a levered product
    products=app.Control_Panel.Products

    if hasattr(productp, '__import_error__'): ie=productp.__import_error__
    else: ie=None

    try: fver=open(home+'/version.txt').read().strip()
    except: fver=''
    old=None
    try:
        if ihasattr(products,name):
            old=getattr(products, name)
            if ihasattr(old,'version') and old.version==fver:
                if hasattr(old, 'import_error_') and \
                   old.import_error_==ie:
                    # Version hasn't changed. Don't reinitialize.
                    return old
    except: pass

    disable_distribution = 1
    try:
        f=CompressedInputFile(open(home+'/product.dat','rb'), name+' shshsh')
    except:
        f=fver and (" (%s)" % fver)
        product=Product(name, 'Installed product %s%s' % (name,f))
    else:
        meta=cPickle.Unpickler(f).load()
        product=app._p_jar.importFile(f)
        if meta.get('redistributable', 0):
            disable_distribution = 0
        product._objects=meta['_objects']

    if old is not None:
        app._manage_remove_product_meta_type(product)
        products._delObject(name)
        for id, v in old.objectItems():
            try: product._setObject(id, v)
            except: pass

    products._setObject(name, product)
    #product.__of__(products)._postCopy(products)
    product.icon='p_/InstalledProduct_icon'
    product.version=fver
    product.home=home
    if disable_distribution:
        product.manage_options=(Folder.manage_options[0],) + \
                                tuple(Folder.manage_options[2:])
        product._distribution=None
        product.manage_distribution=None
    product.thisIsAnInstalledProduct=1

    if ie:
        product.import_error_=ie
        product.title='Broken product %s' % name
        product.icon='p_/BrokenProduct_icon'
        product.manage_options=(
            {'label':'Traceback', 'action':'manage_traceback'},
            )

    for name in ('README.txt', 'README.TXT', 'readme.txt'):
        path = os.path.join(home, name)
        if os.path.isfile(path):
            product.manage_options=product.manage_options+(
                {'label':'README', 'action':'manage_readme'},
                )
            break

    # Ensure this product has a refresh tab.
    found = 0
    for option in product.manage_options:
        if option.get('label') == 'Refresh':
            found = 1
            break
    if not found:
        product.manage_options = product.manage_options + (
            {'label':'Refresh', 'action':'manage_refresh',
             'help': ('OFSP','Product_Refresh.stx')},)

    if not doInstall():
        get_transaction().abort()
        return product

    # Give the ZClass fixup code in Application
    Globals.__disk_product_installed__=1
    return product

def ihasattr(o, name):
    return hasattr(o, name) and o.__dict__.has_key(name)


def doInstall():
    if os.environ.has_key('FORCE_PRODUCT_LOAD'):
        return not not os.environ['FORCE_PRODUCT_LOAD']

    return not os.environ.get('ZEO_CLIENT')
