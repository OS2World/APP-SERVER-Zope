import unittest
from urllib import quote_plus

class RecordTests( unittest.TestCase ):

    def test_repr( self ):
        from ZPublisher.HTTPRequest import record
        record = record()
        record.a = 1
        record.b = 'foo'
        r = repr( record )
        d = eval( r )
        self.assertEqual( d, record.__dict__ )


class ProcessInputsTests(unittest.TestCase):
    def _getHTTPRequest(self, env):
        from ZPublisher.HTTPRequest import HTTPRequest
        return HTTPRequest(None, env, None)

    def _processInputs(self, inputs):
        # Have the inputs processed, and return a HTTPRequest object holding the
        # result.
        # inputs is expected to be a list of (key, value) tuples, no CGI
        # encoding is required.

        query_string = []
        add = query_string.append
        for key, val in inputs:
            add("%s=%s" % (quote_plus(key), quote_plus(val)))
        query_string = '&'.join(query_string)

        env = {'SERVER_NAME': 'testingharnas', 'SERVER_PORT': '80'}
        env['QUERY_STRING'] = query_string
        req = self._getHTTPRequest(env)
        req.processInputs()
        self._noFormValuesInOther(req)
        return req

    def _noTaintedValues(self, req):
        self.failIf(req.taintedform.keys())

    def _valueIsOrHoldsTainted(self, val):
        # Recursively searches a structure for a TaintedString and returns 1
        # when one is found.
        # Also raises an Assertion if a string which *should* have been
        # tainted is found, or when a tainted string is not deemed dangerous.
        from types import ListType, TupleType, StringType, UnicodeType
        from ZPublisher.HTTPRequest import record
        from ZPublisher.TaintedString import TaintedString

        retval = 0

        if isinstance(val, TaintedString):
            self.failIf(not '<' in val,
                        "%r is not dangerous, no taint required." % val)
            retval = 1

        elif isinstance(val, record):
            for attr, value in val.__dict__.items():
                rval = self._valueIsOrHoldsTainted(attr)
                if rval: retval = 1
                rval = self._valueIsOrHoldsTainted(value)
                if rval: retval = 1

        elif type(val) in (ListType, TupleType):
            for entry in val:
                rval = self._valueIsOrHoldsTainted(entry)
                if rval: retval = 1

        elif type(val) in (StringType, UnicodeType):
            self.failIf('<' in val,
                        "'%s' is dangerous and should have been tainted." % val)

        return retval

    def _noFormValuesInOther(self, req):
        for key in req.taintedform.keys():
            self.failIf(req.other.has_key(key),
                'REQUEST.other should not hold tainted values at first!')

        for key in req.form.keys():
            self.failIf(req.other.has_key(key),
                'REQUEST.other should not hold form values at first!')

    def _onlyTaintedformHoldsTaintedStrings(self, req):
        for key, val in req.taintedform.items():
            self.assert_(self._valueIsOrHoldsTainted(key) or
                         self._valueIsOrHoldsTainted(val),
                         'Tainted form holds item %s that is not tainted' % key)

        for key, val in req.form.items():
            if req.taintedform.has_key(key):
                continue
            self.failIf(self._valueIsOrHoldsTainted(key) or
                        self._valueIsOrHoldsTainted(val),
                        'Normal form holds item %s that is tainted' % key)

    def _taintedKeysAlsoInForm(self, req):
        for key in req.taintedform.keys():
            self.assert_(req.form.has_key(key),
                "Found tainted %s not in form" % key)
            self.assertEquals(req.form[key], req.taintedform[key],
                "Key %s not correctly reproduced in tainted; expected %r, "
                "got %r" % (key, req.form[key], req.taintedform[key]))

    def testNoMarshalling(self):
        inputs = (
            ('foo', 'bar'), ('spam', 'eggs'),
            ('number', '1'),
            ('spacey key', 'val'), ('key', 'spacey val'),
            ('multi', '1'), ('multi', '2'))
        req = self._processInputs(inputs)

        formkeys = list(req.form.keys())
        formkeys.sort()
        self.assertEquals(formkeys, ['foo', 'key', 'multi', 'number',
            'spacey key', 'spam'])
        self.assertEquals(req['number'], '1')
        self.assertEquals(req['multi'], ['1', '2'])
        self.assertEquals(req['spacey key'], 'val')
        self.assertEquals(req['key'], 'spacey val')

        self._noTaintedValues(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testSimpleMarshalling(self):
        from DateTime import DateTime

        inputs = (
            ('num:int', '42'), ('fract:float', '4.2'), ('bign:long', '45'),
            ('words:string', 'Some words'), ('2tokens:tokens', 'one two'),
            ('aday:date', '2002/07/23'),
            ('accountedfor:required', 'yes'),
            ('multiline:lines', 'one\ntwo'),
            ('morewords:text', 'one\ntwo\n'))
        req = self._processInputs(inputs)

        formkeys = list(req.form.keys())
        formkeys.sort()
        self.assertEquals(formkeys, ['2tokens', 'accountedfor', 'aday', 'bign',
            'fract', 'morewords', 'multiline', 'num', 'words'])

        self.assertEquals(req['2tokens'], ['one', 'two'])
        self.assertEquals(req['accountedfor'], 'yes')
        self.assertEquals(req['aday'], DateTime('2002/07/23'))
        self.assertEquals(req['bign'], 45L)
        self.assertEquals(req['fract'], 4.2)
        self.assertEquals(req['morewords'], 'one\ntwo\n')
        self.assertEquals(req['multiline'], ['one', 'two'])
        self.assertEquals(req['num'], 42)
        self.assertEquals(req['words'], 'Some words')

        self._noTaintedValues(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testUnicodeConversions(self):
        inputs = (('ustring:ustring:utf8', 'test\xc2\xae'),
                  ('utext:utext:utf8', 'test\xc2\xae\ntest\xc2\xae\n'),
                  ('utokens:utokens:utf8', 'test\xc2\xae test\xc2\xae'),
                  ('ulines:ulines:utf8', 'test\xc2\xae\ntest\xc2\xae'),

                  ('nouconverter:string:utf8', 'test\xc2\xae'))
        req = self._processInputs(inputs)

        formkeys = list(req.form.keys())
        formkeys.sort()
        self.assertEquals(formkeys, ['nouconverter', 'ulines', 'ustring',
            'utext', 'utokens'])

        self.assertEquals(req['ustring'], u'test\u00AE')
        self.assertEquals(req['utext'], u'test\u00AE\ntest\u00AE\n')
        self.assertEquals(req['utokens'], [u'test\u00AE', u'test\u00AE'])
        self.assertEquals(req['ulines'], [u'test\u00AE', u'test\u00AE'])

        # expect a latin1 encoded version
        self.assertEquals(req['nouconverter'], 'test\xae')

        self._noTaintedValues(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testSimpleContainers(self):
        inputs = (
            ('oneitem:list', 'one'),
            ('alist:list', 'one'), ('alist:list', 'two'),
            ('oneitemtuple:tuple', 'one'),
            ('atuple:tuple', 'one'), ('atuple:tuple', 'two'),
            ('onerec.foo:record', 'foo'), ('onerec.bar:record', 'bar'),
            ('setrec.foo:records', 'foo'), ('setrec.bar:records', 'bar'),
            ('setrec.foo:records', 'spam'), ('setrec.bar:records', 'eggs'))
        req = self._processInputs(inputs)

        formkeys = list(req.form.keys())
        formkeys.sort()
        self.assertEquals(formkeys, ['alist', 'atuple', 'oneitem',
            'oneitemtuple', 'onerec', 'setrec'])

        self.assertEquals(req['oneitem'], ['one'])
        self.assertEquals(req['oneitemtuple'], ('one',))
        self.assertEquals(req['alist'], ['one', 'two'])
        self.assertEquals(req['atuple'], ('one', 'two'))
        self.assertEquals(req['onerec'].foo, 'foo')
        self.assertEquals(req['onerec'].bar, 'bar')
        self.assertEquals(len(req['setrec']), 2)
        self.assertEquals(req['setrec'][0].foo, 'foo')
        self.assertEquals(req['setrec'][0].bar, 'bar')
        self.assertEquals(req['setrec'][1].foo, 'spam')
        self.assertEquals(req['setrec'][1].bar, 'eggs')

        self._noTaintedValues(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testMarshallIntoSequences(self):
        inputs = (
            ('ilist:int:list', '1'), ('ilist:int:list', '2'),
            ('ilist:list:int', '3'),
            ('ftuple:float:tuple', '1.0'), ('ftuple:float:tuple', '1.1'),
            ('ftuple:tuple:float', '1.2'),
            ('tlist:tokens:list', 'one two'), ('tlist:list:tokens', '3 4'))
        req = self._processInputs(inputs)

        formkeys = list(req.form.keys())
        formkeys.sort()
        self.assertEquals(formkeys, ['ftuple', 'ilist', 'tlist'])

        self.assertEquals(req['ilist'], [1, 2, 3])
        self.assertEquals(req['ftuple'], (1.0, 1.1, 1.2))
        self.assertEquals(req['tlist'], [['one', 'two'], ['3', '4']])

        self._noTaintedValues(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testRecordsWithSequences(self):
        inputs = (
            ('onerec.name:record', 'foo'),
            ('onerec.tokens:tokens:record', 'one two'),
            ('onerec.ints:int:record', '1'),
            ('onerec.ints:int:record', '2'),

            ('setrec.name:records', 'first'),
            ('setrec.ilist:list:int:records', '1'),
            ('setrec.ilist:list:int:records', '2'),
            ('setrec.ituple:tuple:int:records', '1'),
            ('setrec.ituple:tuple:int:records', '2'),
            ('setrec.name:records', 'second'),
            ('setrec.ilist:list:int:records', '1'),
            ('setrec.ilist:list:int:records', '2'),
            ('setrec.ituple:tuple:int:records', '1'),
            ('setrec.ituple:tuple:int:records', '2'))
        req = self._processInputs(inputs)

        formkeys = list(req.form.keys())
        formkeys.sort()
        self.assertEquals(formkeys, ['onerec', 'setrec'])

        self.assertEquals(req['onerec'].name, 'foo')
        self.assertEquals(req['onerec'].tokens, ['one', 'two'])
        # Implicit sequences and records don't mix.
        self.assertEquals(req['onerec'].ints, 2)

        self.assertEquals(len(req['setrec']), 2)
        self.assertEquals(req['setrec'][0].name, 'first')
        self.assertEquals(req['setrec'][1].name, 'second')

        for i in range(2):
            self.assertEquals(req['setrec'][i].ilist, [1, 2])
            self.assertEquals(req['setrec'][i].ituple, (1, 2))

        self._noTaintedValues(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testDefaults(self):
        inputs = (
            ('foo:default:int', '5'),

            ('alist:int:default', '3'),
            ('alist:int:default', '4'),
            ('alist:int:default', '5'),
            ('alist:int', '1'),
            ('alist:int', '2'),

            ('explicitlist:int:list:default', '3'),
            ('explicitlist:int:list:default', '4'),
            ('explicitlist:int:list:default', '5'),
            ('explicitlist:int:list', '1'),
            ('explicitlist:int:list', '2'),

            ('bar.spam:record:default', 'eggs'),
            ('bar.foo:record:default', 'foo'),
            ('bar.foo:record', 'baz'),

            ('setrec.spam:records:default', 'eggs'),
            ('setrec.foo:records:default', 'foo'),
            ('setrec.foo:records', 'baz'),
            ('setrec.foo:records', 'ham'),
            )
        req = self._processInputs(inputs)

        formkeys = list(req.form.keys())
        formkeys.sort()
        self.assertEquals(formkeys, ['alist', 'bar', 'explicitlist', 'foo',
            'setrec'])

        self.assertEquals(req['alist'], [1, 2, 3, 4, 5])
        self.assertEquals(req['explicitlist'], [1, 2, 3, 4, 5])

        self.assertEquals(req['foo'], 5)
        self.assertEquals(req['bar'].spam, 'eggs')
        self.assertEquals(req['bar'].foo, 'baz')

        self.assertEquals(len(req['setrec']), 2)
        self.assertEquals(req['setrec'][0].spam, 'eggs')
        self.assertEquals(req['setrec'][0].foo, 'baz')
        self.assertEquals(req['setrec'][1].spam, 'eggs')
        self.assertEquals(req['setrec'][1].foo, 'ham')

        self._noTaintedValues(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testNoMarshallingWithTaints(self):
        inputs = (
            ('foo', 'bar'), ('spam', 'eggs'),
            ('number', '1'),
            ('tainted', '<tainted value>'),
            ('<tainted key>', 'value'),
            ('spacey key', 'val'), ('key', 'spacey val'),
            ('tinitmulti', '<1>'), ('tinitmulti', '2'),
            ('tdefermulti', '1'), ('tdefermulti', '<2>'),
            ('tallmulti', '<1>'), ('tallmulti', '<2>'))
        req = self._processInputs(inputs)

        taintedformkeys = list(req.taintedform.keys())
        taintedformkeys.sort()
        self.assertEquals(taintedformkeys, ['<tainted key>', 'tainted',
            'tallmulti', 'tdefermulti', 'tinitmulti'])

        self._taintedKeysAlsoInForm(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testSimpleMarshallingWithTaints(self):
        inputs = (
            ('<tnum>:int', '42'), ('<tfract>:float', '4.2'),
            ('<tbign>:long', '45'),
            ('twords:string', 'Some <words>'), ('t2tokens:tokens', 'one <two>'),
            ('<taday>:date', '2002/07/23'),
            ('taccountedfor:required', '<yes>'),
            ('tmultiline:lines', '<one\ntwo>'),
            ('tmorewords:text', '<one\ntwo>\n'))
        req = self._processInputs(inputs)

        taintedformkeys = list(req.taintedform.keys())
        taintedformkeys.sort()
        self.assertEquals(taintedformkeys, ['<taday>', '<tbign>', '<tfract>',
            '<tnum>', 't2tokens', 'taccountedfor', 'tmorewords', 'tmultiline',
            'twords'])

        self._taintedKeysAlsoInForm(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testUnicodeWithTaints(self):
        inputs = (('tustring:ustring:utf8', '<test\xc2\xae>'),
                  ('tutext:utext:utf8', '<test\xc2\xae>\n<test\xc2\xae\n>'),

                  ('tinitutokens:utokens:utf8', '<test\xc2\xae> test\xc2\xae'),
                  ('tinitulines:ulines:utf8', '<test\xc2\xae>\ntest\xc2\xae'),

                  ('tdeferutokens:utokens:utf8', 'test\xc2\xae <test\xc2\xae>'),
                  ('tdeferulines:ulines:utf8', 'test\xc2\xae\n<test\xc2\xae>'),

                  ('tnouconverter:string:utf8', '<test\xc2\xae>'))
        req = self._processInputs(inputs)

        taintedformkeys = list(req.taintedform.keys())
        taintedformkeys.sort()
        self.assertEquals(taintedformkeys, ['tdeferulines', 'tdeferutokens',
            'tinitulines', 'tinitutokens', 'tnouconverter', 'tustring',
            'tutext'])

        self._taintedKeysAlsoInForm(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testSimpleContainersWithTaints(self):
        from types import ListType, TupleType
        from ZPublisher.HTTPRequest import record

        inputs = (
            ('toneitem:list', '<one>'),
            ('<tkeyoneitem>:list', 'one'),
            ('tinitalist:list', '<one>'), ('tinitalist:list', 'two'),
            ('tdeferalist:list', 'one'), ('tdeferalist:list', '<two>'),

            ('toneitemtuple:tuple', '<one>'),
            ('tinitatuple:tuple', '<one>'), ('tinitatuple:tuple', 'two'),
            ('tdeferatuple:tuple', 'one'), ('tdeferatuple:tuple', '<two>'),

            ('tinitonerec.foo:record', '<foo>'),
            ('tinitonerec.bar:record', 'bar'),
            ('tdeferonerec.foo:record', 'foo'),
            ('tdeferonerec.bar:record', '<bar>'),

            ('tinitinitsetrec.foo:records', '<foo>'),
            ('tinitinitsetrec.bar:records', 'bar'),
            ('tinitinitsetrec.foo:records', 'spam'),
            ('tinitinitsetrec.bar:records', 'eggs'),

            ('tinitdefersetrec.foo:records', 'foo'),
            ('tinitdefersetrec.bar:records', '<bar>'),
            ('tinitdefersetrec.foo:records', 'spam'),
            ('tinitdefersetrec.bar:records', 'eggs'),

            ('tdeferinitsetrec.foo:records', 'foo'),
            ('tdeferinitsetrec.bar:records', 'bar'),
            ('tdeferinitsetrec.foo:records', '<spam>'),
            ('tdeferinitsetrec.bar:records', 'eggs'),

            ('tdeferdefersetrec.foo:records', 'foo'),
            ('tdeferdefersetrec.bar:records', 'bar'),
            ('tdeferdefersetrec.foo:records', 'spam'),
            ('tdeferdefersetrec.bar:records', '<eggs>'))
        req = self._processInputs(inputs)

        taintedformkeys = list(req.taintedform.keys())
        taintedformkeys.sort()
        self.assertEquals(taintedformkeys, ['<tkeyoneitem>', 'tdeferalist',
            'tdeferatuple', 'tdeferdefersetrec', 'tdeferinitsetrec',
            'tdeferonerec', 'tinitalist', 'tinitatuple', 'tinitdefersetrec',
            'tinitinitsetrec', 'tinitonerec', 'toneitem', 'toneitemtuple'])

        self._taintedKeysAlsoInForm(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testRecordsWithSequencesAndTainted(self):
        inputs = (
            ('tinitonerec.tokens:tokens:record', '<one> two'),
            ('tdeferonerec.tokens:tokens:record', 'one <two>'),

            ('tinitsetrec.name:records', 'first'),
            ('tinitsetrec.ilist:list:records', '<1>'),
            ('tinitsetrec.ilist:list:records', '2'),
            ('tinitsetrec.ituple:tuple:int:records', '1'),
            ('tinitsetrec.ituple:tuple:int:records', '2'),
            ('tinitsetrec.name:records', 'second'),
            ('tinitsetrec.ilist:list:records', '1'),
            ('tinitsetrec.ilist:list:records', '2'),
            ('tinitsetrec.ituple:tuple:int:records', '1'),
            ('tinitsetrec.ituple:tuple:int:records', '2'),

            ('tdeferfirstsetrec.name:records', 'first'),
            ('tdeferfirstsetrec.ilist:list:records', '1'),
            ('tdeferfirstsetrec.ilist:list:records', '<2>'),
            ('tdeferfirstsetrec.ituple:tuple:int:records', '1'),
            ('tdeferfirstsetrec.ituple:tuple:int:records', '2'),
            ('tdeferfirstsetrec.name:records', 'second'),
            ('tdeferfirstsetrec.ilist:list:records', '1'),
            ('tdeferfirstsetrec.ilist:list:records', '2'),
            ('tdeferfirstsetrec.ituple:tuple:int:records', '1'),
            ('tdeferfirstsetrec.ituple:tuple:int:records', '2'),

            ('tdefersecondsetrec.name:records', 'first'),
            ('tdefersecondsetrec.ilist:list:records', '1'),
            ('tdefersecondsetrec.ilist:list:records', '2'),
            ('tdefersecondsetrec.ituple:tuple:int:records', '1'),
            ('tdefersecondsetrec.ituple:tuple:int:records', '2'),
            ('tdefersecondsetrec.name:records', 'second'),
            ('tdefersecondsetrec.ilist:list:records', '1'),
            ('tdefersecondsetrec.ilist:list:records', '<2>'),
            ('tdefersecondsetrec.ituple:tuple:int:records', '1'),
            ('tdefersecondsetrec.ituple:tuple:int:records', '2'),
            )
        req = self._processInputs(inputs)

        taintedformkeys = list(req.taintedform.keys())
        taintedformkeys.sort()
        self.assertEquals(taintedformkeys, ['tdeferfirstsetrec', 'tdeferonerec',
            'tdefersecondsetrec', 'tinitonerec', 'tinitsetrec'])

        self._taintedKeysAlsoInForm(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testDefaultsWithTaints(self):
        inputs = (
            ('tfoo:default', '<5>'),

            ('doesnnotapply:default', '<4>'),
            ('doesnnotapply', '4'),

            ('tinitlist:default', '3'),
            ('tinitlist:default', '4'),
            ('tinitlist:default', '5'),
            ('tinitlist', '<1>'),
            ('tinitlist', '2'),

            ('tdeferlist:default', '3'),
            ('tdeferlist:default', '<4>'),
            ('tdeferlist:default', '5'),
            ('tdeferlist', '1'),
            ('tdeferlist', '2'),

            ('tinitbar.spam:record:default', 'eggs'),
            ('tinitbar.foo:record:default', 'foo'),
            ('tinitbar.foo:record', '<baz>'),
            ('tdeferbar.spam:record:default', '<eggs>'),
            ('tdeferbar.foo:record:default', 'foo'),
            ('tdeferbar.foo:record', 'baz'),

            ('rdoesnotapply.spam:record:default', '<eggs>'),
            ('rdoesnotapply.spam:record', 'eggs'),

            ('tinitsetrec.spam:records:default', 'eggs'),
            ('tinitsetrec.foo:records:default', 'foo'),
            ('tinitsetrec.foo:records', '<baz>'),
            ('tinitsetrec.foo:records', 'ham'),

            ('tdefersetrec.spam:records:default', '<eggs>'),
            ('tdefersetrec.foo:records:default', 'foo'),
            ('tdefersetrec.foo:records', 'baz'),
            ('tdefersetrec.foo:records', 'ham'),

            ('srdoesnotapply.foo:records:default', '<eggs>'),
            ('srdoesnotapply.foo:records', 'baz'),
            ('srdoesnotapply.foo:records', 'ham'))
        req = self._processInputs(inputs)

        taintedformkeys = list(req.taintedform.keys())
        taintedformkeys.sort()
        self.assertEquals(taintedformkeys, ['tdeferbar', 'tdeferlist',
            'tdefersetrec', 'tfoo', 'tinitbar', 'tinitlist', 'tinitsetrec'])

        self._taintedKeysAlsoInForm(req)
        self._onlyTaintedformHoldsTaintedStrings(req)

    def testTaintedAttributeRaises(self):
        input = ('taintedattr.here<be<taint:record', 'value',)

        self.assertRaises(ValueError, self._processInputs, input)

    def testNoTaintedExceptions(self):
        # Feed tainted garbage to the conversion methods, and any exception
        # returned should be HTML safe
        from ZPublisher.Converters import type_converters
        from DateTime import DateTime
        for type, convert in type_converters.items():
            try:
                convert('<html garbage>')
            except Exception, e:
                self.failIf('<' in e.args,
                    '%s converter does not quote unsafe value!' % type)
            except DateTime.SyntaxError, e:
                self.failIf('<' in e,
                    '%s converter does not quote unsafe value!' % type)

    def testNameWithDotAsTuple(self):
        # Collector #500
        inputs = (
            ('name.:tuple', 'name with dot as tuple'),)
        req = self._processInputs(inputs)

        formkeys = list(req.form.keys())
        formkeys.sort()
        self.assertEquals(formkeys, ['name.'])

        self.assertEquals(req['name.'], ('name with dot as tuple',))

        self._noTaintedValues(req)
        self._onlyTaintedformHoldsTaintedStrings(req)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RecordTests, 'test'))
    suite.addTest(unittest.makeSuite(ProcessInputsTests, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main()
