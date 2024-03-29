import sys, os, time, unittest

if __name__=='__main__':
    sys.path.insert(0, '..')
    sys.path.insert(0, '../../..')

import ZODB # in order to get Persistence.Persistent working
from Testing import makerequest
import Acquisition
from Acquisition import aq_base
from Products.Transience.Transience import TransientObjectContainer
import Products.Transience.Transience
import Products.Transience.TransientObject
from Products.PythonScripts.PythonScript import PythonScript
from ZODB.POSException import InvalidObjectReference
from DateTime import DateTime
from unittest import TestCase, TestSuite, TextTestRunner, makeSuite
from ZODB.DemoStorage import DemoStorage
from OFS.Application import Application
import  threading
import fauxtime
import time as oldtime

WRITEGRANULARITY = 30
stuff = {}

def _getApp():

    app = stuff.get('app', None)
    if not app:
        ds = DemoStorage(quota=(1<<20))
        db = ZODB.DB(ds)
        conn = db.open()
        root = conn.root()
        app = Application()
        root['Application']= app
        get_transaction().commit()
        stuff['app'] = app
        stuff['conn'] = conn
        stuff['db'] = db
    return app

def _openApp():
    conn = stuff['db'].open()
    root = conn.root()
    app = root['Application']
    return conn, app

def _delApp():
    get_transaction().abort()
    stuff['conn'].close()
    del stuff['conn']
    del stuff['app']
    del stuff['db']


class TestBase(TestCase):
    def setUp(self):
        Products.Transience.Transience.time = fauxtime
        Products.Transience.TransientObject.time = fauxtime
        self.app = makerequest.makerequest(_getApp())
        timeout = self.timeout = 1
        sm=TransientObjectContainer(
            id='sm', timeout_mins=timeout, title='SessionThing',
            addNotification=addNotificationTarget,
            delNotification=delNotificationTarget)
        self.app._setObject('sm', sm)

    def tearDown(self):
        get_transaction().abort()
        _delApp()
        del self.app
        Products.Transience.Transience.time = oldtime
        Products.Transience.TransientObject.time = oldtime

class TestLastAccessed(TestBase):
    def testLastAccessed(self):
        sdo = self.app.sm.new_or_existing('TempObject')
        la1 = sdo.getLastAccessed()
        fauxtime.sleep(WRITEGRANULARITY + 1)
        sdo = self.app.sm.get('TempObject')
        assert sdo.getLastAccessed() > la1, (sdo.getLastAccessed(), la1)

class TestNotifications(TestBase):
    def testAddNotification(self):
        self.app.sm.setAddNotificationTarget(addNotificationTarget)
        sdo = self.app.sm.new_or_existing('TempObject')
        now = fauxtime.time()
        k = sdo.get('starttime')
        assert type(k) == type(now)
        assert k <= now

    def testDelNotification(self):
        self.app.sm.setDelNotificationTarget(delNotificationTarget)
        sdo = self.app.sm.new_or_existing('TempObject')
        timeout = self.timeout * 60
        fauxtime.sleep(timeout + (timeout * .75))
        sdo1 = self.app.sm.get('TempObject')
        # force the sdm to do housekeeping
        self.app.sm._housekeep(self.app.sm._deindex_next() -
                                   self.app.sm._period)
        now = fauxtime.time()
        k = sdo.get('endtime')
        assert (type(k) == type(now)), type(k)
        assert k <= now, (k, now)

def addNotificationTarget(item, context):
    item['starttime'] = fauxtime.time()

def delNotificationTarget(item, context):
    item['endtime'] = fauxtime.time()

def test_suite():
    last_accessed = makeSuite(TestLastAccessed, 'test')
    start_end = makeSuite(TestNotifications, 'test')
    suite = TestSuite((start_end, last_accessed))
    return suite

if __name__ == '__main__':
    runner = TextTestRunner(verbosity=9)
    runner.run(test_suite())
