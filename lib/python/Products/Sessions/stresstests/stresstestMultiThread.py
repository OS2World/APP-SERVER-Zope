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
import sys, os, time
if __name__ == "__main__":
    sys.path.insert(0, '../../..')
    #os.chdir('../../..')
from Testing import makerequest
import ZODB # in order to get Persistence.Persistent working
import Acquisition
from Acquisition import aq_base
from Products.Sessions.BrowserIdManager import BrowserIdManager, \
     getNewBrowserId
from Products.Sessions.SessionDataManager import \
    SessionDataManager, SessionDataManagerErr
from Products.Transience.Transience import \
    TransientObjectContainer, TransientObject
from Products.TemporaryFolder.TemporaryFolder import MountedTemporaryFolder
from Products.TemporaryFolder.LowConflictConnection import \
     LowConflictConnection
from ZODB.Connection import Connection
from ZODB.POSException import InvalidObjectReference, ConflictError, \
     ReadConflictError, BTreesConflictError
from DateTime import DateTime
from unittest import TestCase, TestSuite, TextTestRunner, makeSuite
import time, threading, random
from cPickle import UnpickleableError
from ZODB.DemoStorage import DemoStorage
from Products.TemporaryFolder.TemporaryStorage import TemporaryStorage
from OFS.Application import Application
import sys
from zLOG import log_time
sys.setcheckinterval(200)

import fauxtime
import Products.Transience.Transience
import Products.Transience.TransientObject
Products.Transience.Transience.time = fauxtime
Products.Transience.TransientObject.time = fauxtime

tf_name = 'temp_folder'
idmgr_name = 'browser_id_manager'
toc_name = 'temp_transient_container'
sdm_name = 'session_data_manager'

stuff = {}

def _getDB():
    db = stuff.get('db')
    if not db:
        ds = DemoStorage()
        db = ZODB.DB(ds)
        conn = db.open()
        root = conn.root()
        app = Application()
        root['Application']= app
        _populate(app)
        get_transaction().commit()
        stuff['db'] = db
        conn.close()
    return db

def _delDB():
    get_transaction().abort()
    del stuff['db']

class Foo(Acquisition.Implicit): pass

def _populate(app):
    bidmgr = BrowserIdManager(idmgr_name)
    tf = MountedTemporaryFolder(tf_name, title="Temporary Folder")
    toc = TransientObjectContainer(toc_name, title='Temporary '
        'Transient Object Container', timeout_mins=1)
    session_data_manager=SessionDataManager(id=sdm_name,
        path='/'+tf_name+'/'+toc_name, title='Session Data Manager')

    try: app._delObject(idmgr_name)
    except AttributeError: pass

    try: app._delObject(tf_name)
    except AttributeError: pass

    try: app._delObject(sdm_name)
    except AttributeError: pass

    app._setObject(idmgr_name, bidmgr)

    app._setObject(sdm_name, session_data_manager)

    app._setObject(tf_name, tf)
    get_transaction().commit()

    app.temp_folder._setObject(toc_name, toc)
    get_transaction().commit()

class TestMultiThread(TestCase):
    def testOverlappingBrowserIds(self):
        token = getNewBrowserId()
        self.go(token)

    def testNonOverlappingBrowserIds(self):
        token = None
        self.go(token)

    def go(self, token):
        readers = []
        writers = []
        readiters = 100
        writeiters = 100
        readout = []
        writeout = []
        numreaders = 4
        numwriters = 2
        numvaluers = 1
        db = _getDB()
        for i in range(numreaders):
            thread = ReaderThread(db, readiters, token)
            readers.append(thread)
        for i in range(numvaluers):
            thread = ValuesGetterThread(db, readiters, token)
            readers.append(thread)
        for i in range(numwriters):
            thread = WriterThread(db, writeiters, token)
            writers.append(thread)
        for thread in readers:
            thread.start()
            time.sleep(0.1)
        for thread in writers:
            thread.start()
            time.sleep(0.1)
        active = 2
        while active > 1:
            active = threading.activeCount()
            print 'waiting for %s threads' % active
            time.sleep(1)

class BaseReaderWriter(threading.Thread):
    def __init__(self, db, iters, token=None):
        self.conn = db.open()
        self.app = self.conn.root()['Application']
        self.app = makerequest.makerequest(self.app)
        if token is None:
            token = getNewBrowserId()
        self.app.REQUEST.browser_id_ = token
        self.iters = iters
        self.sdm_name = sdm_name
        self.out = []
        threading.Thread.__init__(self)

    def run(self):
        i = 0
        try:
            while 1:
                try:
                    self.run1()
                    return
                except ReadConflictError:
                    print "read conflict"
                except BTreesConflictError:
                    print "btrees conflict"
                except ConflictError:
                    print "general conflict"
                except:
                    get_transaction().abort()
                    print log_time()
                    raise
                i = i + 1
                get_transaction().abort()
                time.sleep(random.randrange(5) * .1)
        finally:
            self.conn.close()
            del self.app
            print i

class ReaderThread(BaseReaderWriter):
    def run1(self):
        session_data_manager = getattr(self.app, self.sdm_name)
        data = session_data_manager.getSessionData(create=1)
        t = time.time()
        data[t] = 1
        get_transaction().commit()
        for i in range(self.iters):
            data = session_data_manager.getSessionData()
            if not data.has_key(t):
                self.out.append(1)
            time.sleep(random.choice(range(3)))
            get_transaction().commit()

class WriterThread(BaseReaderWriter):
    def run1(self):
        session_data_manager = getattr(self.app, self.sdm_name)
        for i in range(self.iters):
            data = session_data_manager.getSessionData()
            data[time.time()] = 1
            n = random.choice(range(3))
            time.sleep(n)
            if n % 2 == 0:
                get_transaction().commit()
            else:
                get_transaction().abort()

class ValuesGetterThread(BaseReaderWriter):
    def run1(self):
        tf = getattr(self.app, tf_name)
        toc = getattr(tf, toc_name)
        for i in range(self.iters):
            print '%s values in toc' % len(toc.values())
            n = random.choice(range(3))
            time.sleep(n)
            if n % 2 == 0:
                get_transaction().commit()
            else:
                get_transaction().abort()


def test_suite():
    test_multithread = makeSuite(TestMultiThread, 'test')
    suite = TestSuite((test_multithread,))
    return suite

if __name__ == '__main__':
    runner = TextTestRunner(verbosity=9, descriptions=9)
    runner.run(test_suite())
