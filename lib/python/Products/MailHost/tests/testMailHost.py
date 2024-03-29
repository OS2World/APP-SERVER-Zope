import os, sys, unittest

import string, cStringIO, re
import ZODB, Acquisition
from Products.MailHost.MailHost import MailHostError, _mungeHeaders

class TestMailHost( unittest.TestCase ):

    def testAllHeaders( self ):
        msg = """To: recipient@domain.com
From: sender@domain.com
Subject: This is the subject

This is the message body."""
        # No additional info
        resmsg, resto, resfrom = _mungeHeaders( msg )
        self.failUnless(resto == ['recipient@domain.com'])
        self.failUnless(resfrom == 'sender@domain.com' )

        # Add duplicated info
        resmsg, resto, resfrom = _mungeHeaders( msg, 'recipient@domain.com', 'sender@domain.com', 'This is the subject' )
        self.failUnless(resto == ['recipient@domain.com'])
        self.failUnless(resfrom == 'sender@domain.com' )

        # Add extra info
        resmsg, resto, resfrom = _mungeHeaders( msg, 'recipient2@domain.com', 'sender2@domain.com', 'This is the real subject' )
        self.failUnless(resto == ['recipient2@domain.com'])
        self.failUnless(resfrom == 'sender2@domain.com' )

    def testMissingHeaders( self ):
        msg = """X-Header: Dummy header

This is the message body."""
        # Doesn't specify to
        self.failUnlessRaises( MailHostError, _mungeHeaders, msg, mfrom='sender@domain.com' )
        # Doesn't specify from
        self.failUnlessRaises( MailHostError, _mungeHeaders, msg, mto='recipient@domain.com' )

    def testNoHeaders( self ):
        msg = """This is the message body."""
        # Doesn't specify to
        self.failUnlessRaises( MailHostError, _mungeHeaders, msg, mfrom='sender@domain.com' )
        # Doesn't specify from
        self.failUnlessRaises( MailHostError, _mungeHeaders, msg, mto='recipient@domain.com' )
        # Specify all
        resmsg, resto, resfrom = _mungeHeaders( msg, 'recipient2@domain.com', 'sender2@domain.com', 'This is the real subject' )
        self.failUnless(resto == ['recipient2@domain.com'])
        self.failUnless(resfrom == 'sender2@domain.com' )

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest( unittest.makeSuite( TestMailHost ) )
    return suite

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__ == '__main__':
    main()
