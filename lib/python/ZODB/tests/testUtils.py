"""Test the routines to convert between long and 64-bit strings"""

import random
import unittest

NUM = 100

from ZODB.utils import U64, p64, u64

class TestUtils(unittest.TestCase):

    small = [random.randrange(1, 1L<<32, int=long)
             for i in range(NUM)]
    large = [random.randrange(1L<<32, 1L<<64, int=long)
             for i in range(NUM)]
    all = small + large

    def checkLongToStringToLong(self):
        for num in self.all:
            s = p64(num)
            n = U64(s)
            self.assertEquals(num, n, "U64() failed")
            n2 = u64(s)
            self.assertEquals(num, n2, "u64() failed")

    def checkKnownConstants(self):
        self.assertEquals("\000\000\000\000\000\000\000\001", p64(1))
        self.assertEquals("\000\000\000\001\000\000\000\000", p64(1L<<32))
        self.assertEquals(u64("\000\000\000\000\000\000\000\001"), 1)
        self.assertEquals(U64("\000\000\000\000\000\000\000\001"), 1)
        self.assertEquals(u64("\000\000\000\001\000\000\000\000"), 1L<<32)
        self.assertEquals(U64("\000\000\000\001\000\000\000\000"), 1L<<32)

def test_suite():
    return unittest.makeSuite(TestUtils, 'check')

if __name__ == "__main__":
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "check"
    unittest.main(testLoader=loader)
