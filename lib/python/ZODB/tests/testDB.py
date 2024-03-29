import time
import unittest

import ZODB
import ZODB.MappingStorage

from ZODB.tests.MinPO import MinPO

class DBTests(unittest.TestCase):

    def setUp(self):
        store = ZODB.MappingStorage.MappingStorage()
        self.db = ZODB.DB(store)

    def tearDown(self):
        self.db.close()

    def dowork(self, version=''):
        c = self.db.open(version)
        r = c.root()
        o = r[time.time()] = MinPO(0)
        get_transaction().commit()
        for i in range(25):
            o.value = MinPO(i)
            get_transaction().commit()
            o = o.value
        print r.items()
        c.close()

    # make sure the basic methods are callable

    def testSets(self):
        # test set methods that have non-trivial implementations
        self.db.setCacheDeactivateAfter(12) # deprecated
        self.db.setCacheSize(15)
        self.db.setVersionCacheDeactivateAfter(12) # deprecated
        self.db.setVersionCacheSize(15)

def test_suite():
    return unittest.makeSuite(DBTests)
