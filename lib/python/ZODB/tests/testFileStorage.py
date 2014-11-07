from __future__ import nested_scopes

import sys, os, unittest
import time
import errno

import ZODB.FileStorage
from ZODB.referencesf import referencesf
from ZODB.Transaction import Transaction
from ZODB import POSException

from ZODB.tests import StorageTestBase, BasicStorage, \
     TransactionalUndoStorage, VersionStorage, \
     TransactionalUndoVersionStorage, PackableStorage, \
     Synchronization, ConflictResolution, HistoryStorage, \
     IteratorStorage, Corruption, RevisionStorage, PersistentStorage, \
     MTStorage, ReadOnlyStorage
from ZODB.tests.StorageTestBase import MinPO, zodb_unpickle
from PersistentMapping import PersistentMapping
from ZODB import DB

class FileStorageTests(
    StorageTestBase.StorageTestBase,
    BasicStorage.BasicStorage,
    TransactionalUndoStorage.TransactionalUndoStorage,
    RevisionStorage.RevisionStorage,
    VersionStorage.VersionStorage,
    TransactionalUndoVersionStorage.TransactionalUndoVersionStorage,
    PackableStorage.PackableStorage,
    Synchronization.SynchronizedStorage,
    ConflictResolution.ConflictResolvingStorage,
    HistoryStorage.HistoryStorage,
    IteratorStorage.IteratorStorage,
    IteratorStorage.ExtendedIteratorStorage,
    PersistentStorage.PersistentStorage,
    MTStorage.MTStorage,
    ReadOnlyStorage.ReadOnlyStorage
    ):

    def open(self, **kwargs):
        if kwargs:
            self._storage = apply(ZODB.FileStorage.FileStorage,
                                  ('FileStorageTests.fs',), kwargs)
        else:
            self._storage = ZODB.FileStorage.FileStorage(
                'FileStorageTests.fs', **kwargs)

    def setUp(self):
        self.open(create=1)

    def tearDown(self):
        self._storage.close()
        StorageTestBase.removefs("FileStorageTests.fs")

    def checkLongMetadata(self):
        s = "X" * 75000
        try:
            self._dostore(user=s)
        except POSException.StorageError:
            pass
        else:
            self.fail("expect long user field to raise error")
        try:
            self._dostore(description=s)
        except POSException.StorageError:
            pass
        else:
            self.fail("expect long user field to raise error")

    def check_use_fsIndex(self):
        from ZODB.fsIndex import fsIndex

        self.assertEqual(self._storage._index.__class__, fsIndex)

    # XXX We could really use some tests for sanity checking

    def check_conversion_to_fsIndex_not_if_readonly(self):

        self.tearDown()

        class OldFileStorage(ZODB.FileStorage.FileStorage):
            def _newIndexes(self):
                return {}, {}, {}, {}


        from ZODB.fsIndex import fsIndex
        
        # Hack FileStorage to create dictionary indexes
        self._storage = OldFileStorage('FileStorageTests.fs')

        self.assertEqual(type(self._storage._index), type({}))
        for i in range(10):
            self._dostore()
            
        # Should save the index
        self._storage.close()

        self._storage = ZODB.FileStorage.FileStorage(
            'FileStorageTests.fs', read_only=1)
        self.assertEqual(type(self._storage._index), type({}))
    
    def check_conversion_to_fsIndex(self):

        self.tearDown()

        class OldFileStorage(ZODB.FileStorage.FileStorage):
            def _newIndexes(self):
                return {}, {}, {}, {}


        from ZODB.fsIndex import fsIndex
        
        # Hack FileStorage to create dictionary indexes
        self._storage = OldFileStorage('FileStorageTests.fs')

        self.assertEqual(type(self._storage._index), type({}))
        for i in range(10):
            self._dostore()
            
        oldindex = self._storage._index.copy()
            
        # Should save the index
        self._storage.close()

        self._storage = ZODB.FileStorage.FileStorage('FileStorageTests.fs')
        self.assertEqual(self._storage._index.__class__, fsIndex)
        self.failUnless(self._storage._used_index)

        index = {}
        for k, v in self._storage._index.items():
            index[k] = v

        self.assertEqual(index, oldindex)


    def check_save_after_load_with_no_index(self):
        for i in range(10):
            self._dostore()
        self._storage.close()
        os.remove('FileStorageTests.fs.index')
        self.open()
        self.assertEqual(self._storage._saved, 1)


    # This would make the unit tests too slow
    # check_save_after_load_that_worked_hard(self)        

    def check_periodic_save_index(self):

        # Check the basic algorithm
        oldsaved = self._storage._saved
        self._storage._records_before_save = 10
        for i in range(4):
            self._dostore()
        self.assertEqual(self._storage._saved, oldsaved)
        self._dostore()
        self.assertEqual(self._storage._saved, oldsaved+1)

        # Now make sure the parameter changes as we get bigger
        for i in range(20):
            self._dostore()

        self.failUnless(self._storage._records_before_save > 20)
        

class FileStorageRecoveryTest(
    StorageTestBase.StorageTestBase,
    IteratorStorage.IteratorDeepCompare,
    ):

    def setUp(self):
        StorageTestBase.removefs("Source.fs")
        StorageTestBase.removefs("Dest.fs")
        self._storage = ZODB.FileStorage.FileStorage('Source.fs')
        self._dst = ZODB.FileStorage.FileStorage('Dest.fs')

    def tearDown(self):
        self._storage.close()
        self._dst.close()
        StorageTestBase.removefs("Source.fs")
        StorageTestBase.removefs("Dest.fs")

    def checkSimpleRecovery(self):
        oid = self._storage.new_oid()
        revid = self._dostore(oid, data=11)
        revid = self._dostore(oid, revid=revid, data=12)
        revid = self._dostore(oid, revid=revid, data=13)
        self._dst.copyTransactionsFrom(self._storage)
        self.compare(self._storage, self._dst)

    def checkRecoveryAcrossVersions(self):
        oid = self._storage.new_oid()
        revid = self._dostore(oid, data=21)
        revid = self._dostore(oid, revid=revid, data=22)
        revid = self._dostore(oid, revid=revid, data=23, version='one')
        revid = self._dostore(oid, revid=revid, data=34, version='one')
        self._commitVersion("one", "")
        self._dst.copyTransactionsFrom(self._storage)
        self.compare(self._storage, self._dst)

    def checkRecoverAbortVersion(self):
        oid = self._storage.new_oid()
        revid = self._dostore(oid, data=21, version="one")
        revid = self._dostore(oid, revid=revid, data=23, version='one')
        revid = self._dostore(oid, revid=revid, data=34, version='one')
        oids = self._abortVersion("one")
        self.assertEqual(oids, [oid])
        self._dst.copyTransactionsFrom(self._storage)
        self.compare(self._storage, self._dst)
        # Also make sure the the last transaction has a data record
        # with None for its data attribute, because we've undone the
        # object.
        for s in self._storage, self._dst:
            iter = s.iterator()
            for trans in iter:
                pass # iterate until we get the last one
            data = trans[0]
            self.assertRaises(IndexError, lambda i:trans[i], 1)
            iter.close()
            self.assertEqual(data.oid, oid)
            self.assertEqual(data.data, None)

    def checkRecoverUndoInVersion(self):
        oid = self._storage.new_oid()
        version = "aVersion"
        revid_a = self._dostore(oid, data=MinPO(91))
        revid_b = self._dostore(oid, revid=revid_a, version=version,
                                data=MinPO(92))
        revid_c = self._dostore(oid, revid=revid_b, version=version,
                                data=MinPO(93))
        self._undo(self._storage.undoInfo()[0]['id'], oid)
        self._commitVersion(version, '')
        self._undo(self._storage.undoInfo()[0]['id'], oid)

        # now copy the records to a new storage
        self._dst.copyTransactionsFrom(self._storage)
        self.compare(self._storage, self._dst)

        # The last two transactions were applied directly rather than
        # copied.  So we can't use compare() to verify that they new
        # transactions are applied correctly.  (The new transactions
        # will have different timestamps for each storage.)

        self._abortVersion(version)
        self.assert_(self._storage.versionEmpty(version))
        self._undo(self._storage.undoInfo()[0]['id'], oid)
        self.assert_(not self._storage.versionEmpty(version))

        # check the data is what we expect it to be
        data, revid = self._storage.load(oid, version)
        self.assertEqual(zodb_unpickle(data), MinPO(92))
        data, revid = self._storage.load(oid, '')
        self.assertEqual(zodb_unpickle(data), MinPO(91))

        # and swap the storages
        tmp = self._storage
        self._storage = self._dst
        self._abortVersion(version)
        self.assert_(self._storage.versionEmpty(version))
        self._undo(self._storage.undoInfo()[0]['id'], oid)
        self.assert_(not self._storage.versionEmpty(version))

        # check the data is what we expect it to be
        data, revid = self._storage.load(oid, version)
        self.assertEqual(zodb_unpickle(data), MinPO(92))
        data, revid = self._storage.load(oid, '')
        self.assertEqual(zodb_unpickle(data), MinPO(91))

        # swap them back
        self._storage = tmp

        # Now remove _dst and copy all the transactions a second time.
        # This time we will be able to confirm via compare().
        self._dst.close()
        StorageTestBase.removefs("Dest.fs")
        self._dst = ZODB.FileStorage.FileStorage('Dest.fs')
        self._dst.copyTransactionsFrom(self._storage)
        self.compare(self._storage, self._dst)

    def checkRestoreAcrossPack(self):
        db = DB(self._storage)
        c = db.open()
        r = c.root()
        obj1 = r["obj1"] = MinPO(1)
        get_transaction().commit()
        obj1 = r["obj2"] = MinPO(1)
        get_transaction().commit()

        self._dst.copyTransactionsFrom(self._storage)
        self._dst.pack(time.time(), referencesf)

        self._undo(self._storage.undoInfo()[0]['id'])

        # copy the final transaction manually.  even though there
        # was a pack, the restore() ought to succeed.
        siter = self._storage.iterator()
        final = list(siter)[-1]
        self._dst.tpc_begin(final, final.tid, final.status)
        for r in final:
            self._dst.restore(r.oid, r.serial, r.data, r.version, r.data_txn,
                         final)
        siter.close()
        self._dst.tpc_vote(final)
        self._dst.tpc_finish(final)


def test_suite():
    suite = unittest.makeSuite(FileStorageTests, 'check')
    suite2 = unittest.makeSuite(Corruption.FileStorageCorruptTests, 'check')
    suite3 = unittest.makeSuite(FileStorageRecoveryTest, 'check')
    suite.addTest(suite2)
    suite.addTest(suite3)
    return suite

def main():
    alltests=test_suite()
    runner = unittest.TextTestRunner()
    runner.run(alltests)

def debug():
    test_suite().debug()

def pdebug():
    import pdb
    pdb.run('debug()')

if __name__=='__main__':
    if len(sys.argv) > 1:
        globals()[sys.argv[1]]()
    else:
        main()
