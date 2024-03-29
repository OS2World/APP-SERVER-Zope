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

import os, sys, unittest

from Products.PluginIndexes.PathIndex.PathIndex import PathIndex


class Dummy:

    meta_type="foo"
    def __init__( self, path):
        self.path = path

    def getPhysicalPath(self):
        return self.path.split('/')


    def __str__( self ):
        return '<Dummy: %s>' % self.path

    __repr__ = __str__

class TestCase( unittest.TestCase ):
    """ Test PathIndex objects """

    def setUp(self):
        self._index = PathIndex( 'path' )
        self._values = {
          1 : Dummy("/aa/aa/aa/1.html"),
          2 : Dummy("/aa/aa/bb/2.html"),
          3 : Dummy("/aa/aa/cc/3.html"),
          4 : Dummy("/aa/bb/aa/4.html"),
          5 : Dummy("/aa/bb/bb/5.html"),
          6 : Dummy("/aa/bb/cc/6.html"),
          7 : Dummy("/aa/cc/aa/7.html"),
          8 : Dummy("/aa/cc/bb/8.html"),
          9 : Dummy("/aa/cc/cc/9.html"),
          10 : Dummy("/bb/aa/aa/10.html"),
          11 : Dummy("/bb/aa/bb/11.html"),
          12 : Dummy("/bb/aa/cc/12.html"),
          13 : Dummy("/bb/bb/aa/13.html"),
          14 : Dummy("/bb/bb/bb/14.html"),
          15 : Dummy("/bb/bb/cc/15.html"),
          16 : Dummy("/bb/cc/aa/16.html"),
          17 : Dummy("/bb/cc/bb/17.html"),
          18 : Dummy("/bb/cc/cc/18.html")
        }

    def _populateIndex(self):
        for k, v in self._values.items():
            self._index.index_object( k, v )

    def testEmpty(self):

        assert len( self._index ) == 0
        assert self._index.getEntryForObject( 1234 ) is None
        self._index.unindex_object( 1234 ) # nothrow
        assert self._index._apply_index( {"suxpath":"xxx"} ) is None

    def testUnIndex(self):

        self._populateIndex()

        for k in self._values.keys():
            self._index.unindex_object(k)

        assert len(self._index._index)==0
        assert len(self._index._unindex)==0

    def testUnIndexError(self):
        self._populateIndex()
        
        # this should not raise an error
        self._index.unindex_object(-1)

        # nor should this
        self._index._unindex[1] = "/broken/thing"
        self._index.unindex_object(1)

    def testRoot(self):

        self._populateIndex()

        tests = [
            ("/",0, range(1,19)),
        ]

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':path,"level":level}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':( (path,level),)}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)


    def testSimpleTests(self):

        self._populateIndex()

        tests = [
            ("aa", 0, [1,2,3,4,5,6,7,8,9]),
            ("aa", 1, [1,2,3,10,11,12] ),
            ("bb", 0, [10,11,12,13,14,15,16,17,18]),
            ("bb", 1, [4,5,6,13,14,15] ),
            ("bb/cc", 0, [16,17,18] ),
            ("bb/cc", 1, [6,15] ),
            ("bb/aa", 0, [10,11,12] ),
            ("bb/aa", 1, [4,13] ),
            ("aa/cc", -1, [3,7,8,9,12] ),
            ("bb/bb", -1, [5,13,14,15] ),
            ("18.html", 3, [18] ),
            ("18.html", -1, [18] ),
            ("cc/18.html", -1, [18] ),
            ("cc/18.html", 2, [18] ),

        ]

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':path,"level":level}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':( (path,level),)}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

    def testComplexOrTests(self):

        self._populateIndex()

        tests = [
            (['aa','bb'],1,[1,2,3,4,5,6,10,11,12,13,14,15]),
            (['aa','bb','xx'],1,[1,2,3,4,5,6,10,11,12,13,14,15]),
            ([('cc',1),('cc',2)],0,[3,6,7,8,9,12,15,16,17,18]),
        ]

        for lst ,level,results in tests:

            res = self._index._apply_index(
                            {"path":{'query':lst,"level":level,"operator":"or"}})
            lst = list(res[0].keys())
            self.assertEqual(lst,results)

    def testComplexANDTests(self):

        self._populateIndex()

        tests = [
            (['aa','bb'],1,[]),
            ([('aa',0),('bb',1)],0,[4,5,6]),
            ([('aa',0),('cc',2)],0,[3,6,9]),
        ]

        for lst ,level,results in tests:

            res = self._index._apply_index(
                            {"path":{'query':lst,"level":level,"operator":"and"}})
            lst = list(res[0].keys())
            self.assertEqual(lst,results)

def test_suite():
    return unittest.makeSuite( TestCase )

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__ == '__main__':
    main()
