##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""Demo ZODB storage

The Demo storage serves two purposes:

  - Provide an example implementation of a full storage without
    distracting storage details,

  - Provide a volatile storage that is useful for giving demonstrations.

The demo strorage can have a "base" storage that is used in a
read-only fashion. The base storage must not not to contain version
data.

There are three main data structures:

  _data -- Transaction logging information necessary for undo

      This is a mapping from transaction id to transaction, where
      a transaction is simply a 5-tuple:

        packed, user, description, extension_data, records

      where extension_data is a dictionary or None and records are the
      actual records in chronological order. Packed is a flag
      indicating whethe the transaction has been packed or not

  _index -- A mapping from oid to record

  _vindex -- A mapping from version name to version data

      where version data is a mapping from oid to record

A record is a tuple:

  oid, serial, pre, vdata, p,

where:

     oid -- object id

     serial -- object serial number

     pre -- The previous record for this object (or None)

     vdata -- version data

        None if not a version, ortherwise:
           version, non-version-record

     p -- the pickle data or None

The pickle data will be None for a record for an object created in
an aborted version.

It is instructive to watch what happens to the internal data structures
as changes are made.  For example, in Zope, you can create an external
method::

  import Zope

  def info(RESPONSE):
      RESPONSE['Content-type']= 'text/plain'

      return Zope.DB._storage._splat()

and call it to monitor the storage.

"""
__version__='$Revision: 1.14 $'[11:-2]

import base64, time, string
from ZODB import POSException, BaseStorage, utils
from TimeStamp import TimeStamp
from cPickle import loads
from BTrees import OOBTree

class DemoStorage(BaseStorage.BaseStorage):

    def __init__(self, name='Demo Storage', base=None, quota=None):

        BaseStorage.BaseStorage.__init__(self, name, base)

        # We use a BTree because the items are sorted!
        self._data=OOBTree.OOBTree()
        self._index={}
        self._vindex={}
        self._base=base
        self._size=0
        self._quota=quota
        self._clear_temp()
        if base is not None and base.versions():
            raise POSException.StorageError, (
                "Demo base storage has version data")


    def __len__(self):
        base=self._base
        return (base and len(base) or 0) + len(self._index)

    def getSize(self):
        s=100
        for tid, (p, u, d, e, t) in self._data.items():
            s=s+16+24+12+4+16+len(u)+16+len(d)+16+len(e)+16
            for oid, serial, pre, vdata, p in t:
                s=s+16+24+24+4+4+(p and (16+len(p)) or 4)
                if vdata: s=s+12+16+len(vdata[0])+4

        s=s+16*len(self._index)

        for v in self._vindex.values():
            s=s+32+16*len(v)

        self._size=s
        return s

    def abortVersion(self, src, transaction):
        if transaction is not self._transaction:
            raise POSException.StorageTransactionError(self, transaction)
        if not src:
            raise POSException.VersionCommitError("Invalid version")

        self._lock_acquire()
        try:
            v = self._vindex.get(src, None)
            if not v:
                return

            oids = []
            for r in v.values():
                oid, serial, pre, (version, nv), p = r
                if nv:
                    oids.append(oid)
                    oid, serial, pre, vdata, p = nv
                    self._tindex.append([oid, serial, r, None, p])
                else:
                    # effectively, delete the thing
                    self._tindex.append([oid, None, r, None, None])

            return oids

        finally: self._lock_release()

    def commitVersion(self, src, dest, transaction):
        if transaction is not self._transaction:
            raise POSException.StorageTransactionError(self, transaction)

        if not src:
            raise POSException.VersionCommitError("Invalid source version")
        if src == dest:
            raise POSException.VersionCommitError(
                "Can't commit to same version: %s" % repr(src))

        self._lock_acquire()
        try:
            v=self._vindex.get(src, None)
            if v is None: return

            newserial = self._serial
            tindex=self._tindex
            oids=[]
            for r in v.values():
                oid, serial, pre, vdata, p = r
                assert vdata is not None
                oids.append(oid)
                if dest:
                    new_vdata = dest, vdata[1]
                else:
                    new_vdata = None
                tindex.append([oid, newserial, r, new_vdata, p])


            return oids

        finally: self._lock_release()

    def load(self, oid, version):
        self._lock_acquire()
        try:
            try:
                oid, serial, pre, vdata, p = self._index[oid]
            except KeyError:
                if self._base:
                    return self._base.load(oid, '')
                raise KeyError, oid

            if vdata:
                oversion, nv = vdata
                if oversion != version:
                    if nv:
                        oid, serial, pre, vdata, p = nv
                    else:
                        raise KeyError, oid

            if p is None:
                raise KeyError, oid

            return p, serial
        finally: self._lock_release()

    def modifiedInVersion(self, oid):
        self._lock_acquire()
        try:
            try:
                oid, serial, pre, vdata, p = self._index[oid]
                if vdata: return vdata[0]
                return ''
            except: return ''
        finally: self._lock_release()

    def store(self, oid, serial, data, version, transaction):
        if transaction is not self._transaction:
            raise POSException.StorageTransactionError(self, transaction)

        self._lock_acquire()
        try:
            old=self._index.get(oid, None)
            if old is None:
                # Hm, nothing here, check the base version:
                try: p, oserial = self._base.load(oid, '')
                except: pass
                else:
                    old= oid, oserial, None, None, p

            nv=None
            if old:
                oid, oserial, pre, vdata, p = old

                if vdata:
                    if vdata[0] != version:
                        raise POSException.VersionLockError, oid

                    nv=vdata[1]
                else:
                    nv=old

                if serial != oserial:
                    raise POSException.ConflictError(serials=(oserial, serial))

            serial=self._serial
            r=[oid, serial, old, version and (version, nv) or None, data]
            self._tindex.append(r)

            s=self._tsize
            s=s+72+(data and (16+len(data)) or 4)
            if version: s=s+32+len(version)

            if self._quota is not None and s > self._quota:
                raise POSException.StorageError, (
                    '''<b>Quota Exceeded</b><br>
                    The maximum quota for this demonstration storage
                    has been exceeded.<br>Have a nice day.''')

        finally: self._lock_release()
        return serial

    def supportsUndo(self): return 1
    def supportsVersions(self): return 1

    def _clear_temp(self):
        self._tindex = []
        self._tsize = self._size + 160

    def _begin(self, tid, u, d, e):
        self._tsize = self._size + 120 + len(u) + len(d) + len(e)

    def _finish(self, tid, user, desc, ext):
        self._size = self._tsize

        self._data[tid] = None, user, desc, ext, tuple(self._tindex)
        for r in self._tindex:
            oid, serial, pre, vdata, p = r
            old = self._index.get(oid)
            # If the object had version data, remove the version data.
            if old is not None:
                oldvdata = old[3]
                if oldvdata:
                    v = self._vindex[oldvdata[0]]
                    del v[oid]
                    if not v:
                        # If the version info is now empty, remove it.
                        del self._vindex[oldvdata[0]]

            self._index[oid] = r

            # If there is version data, then udpate self._vindex, too.
            if vdata:
                version = vdata[0]
                v = self._vindex.get(version)
                if v is None:
                    v = self._vindex[version] = {}
                v[oid] = r

    def undo(self, transaction_id):
        self._lock_acquire()
        try:
            transaction_id=base64.decodestring(transaction_id+'\n')
            try: t=self._data[transaction_id][4]
            except KeyError:
                raise UndoError, 'Invalid undo transaction id'

            index=self._index
            vindex=self._vindex
            vindex_get=self._vindex.get
            for r in t:
                if index[r[0]] is not r:
                    raise POSException.UndoError, 'non-undoable transaction'

            oids=[]
            for r in t:
                oid, serial, pre, vdata, p = r
                if pre:

                    index[oid] = pre
                    oids.append(oid)

                    # Delete old version data
                    if vdata:
                        version=vdata[0]
                        v=vindex.get(version, None)
                        if v: del v[oid]

                    # Add new version data (from pre):
                    oid, serial, prepre, vdata, p = pre
                    if vdata:
                        version=vdata[0]
                        v=vindex.get(version, None)
                        if v is None: v=vindex[version]={}
                        v[oid]=pre

                else:
                    del index[oid]
                    if vdata:
                        version=vdata[0]
                        v=vindex.get(version, None)
                        if v: del v[oid]
                        if not v: del vindex[version]

            del self._data[transaction_id]

            return oids

        finally: self._lock_release()

    def undoLog(self, first, last, filter=None):
        # I think this is wrong given the handling of first and last
        # in FileStorage.
        self._lock_acquire()
        try:
            transactions = self._data.items()
            pos = len(transactions)
            r = []
            i = 0
            while i < last and pos:
                pos = pos - 1
                if i < first:
                    i = i + 1
                    continue
                tid, (p, u, d, e, t) = transactions[pos]
                if p:
                    continue
                d = {'id': base64.encodestring(tid)[:-1],
                     'time': TimeStamp(tid).timeTime(),
                     'user_name': u, 'description': d}
                if e:
                    d.update(loads(e))

                if filter is None or filter(d):
                    r.append(d)
                    i = i + 1
            return r
        finally:
            self._lock_release()

    def versionEmpty(self, version):
        return not self._vindex.get(version, None)

    def versions(self, max=None):
        r = []
        for v in self._vindex.keys():
            if self.versionEmpty(v):
                continue
            r.append(v)
            if max is not None and len(r) >= max:
                break
        return r

    def _build_indexes(self, stop='\377\377\377\377\377\377\377\377'):
        # Rebuild index structures from transaction data
        index={}
        vindex={}
        _data=self._data
        for tid, (p, u, d, e, t) in _data.items():
            if tid >= stop: break
            for r in t:
                oid, serial, pre, vdata, p = r
                old=index.get(oid, None)

                if old is not None:
                    oldvdata=old[3]
                    if oldvdata:
                        v=vindex[oldvdata[0]]
                        del v[oid]
                        if not v: del vindex[oldvdata[0]]

                index[oid]=r

                if vdata:
                    version=vdata[0]
                    v=vindex.get(version, None)
                    if v is None: v=vindex[version]={}
                    vindex[vdata[0]][oid]=r

        return index, vindex

    def pack(self, t, referencesf):
        # Packing is hard, at least when undo is supported.
        # Even for a simple storage like this one, packing
        # is pretty complex.

        self._lock_acquire()
        try:

            stop=`apply(TimeStamp, time.gmtime(t)[:5]+(t%60,))`
            _data=self._data

            # Build indexes up to the pack time:
            index, vindex = self._build_indexes(stop)

            # Now build an index of *only* those objects reachable
            # from the root.
            rootl=['\0\0\0\0\0\0\0\0']
            pop=rootl.pop
            pindex={}
            referenced=pindex.has_key
            while rootl:
                oid=pop()
                if referenced(oid): continue

                # Scan non-version pickle for references
                r=index.get(oid, None)
                if r is None:
                    # Base storage
                    p, s = self._base.load(oid, '')
                    referencesf(p, rootl)
                else:
                    pindex[oid]=r
                    oid, serial, pre, vdata, p = r
                    referencesf(p, rootl)
                    if vdata:
                        nv=vdata[1]
                        if nv:
                            oid, serial, pre, vdata, p = nv
                            referencesf(p, rootl)

            # Now we're ready to do the actual packing.
            # We'll simply edit the transaction data in place.
            # We'll defer deleting transactions till the end
            # to avoid messing up the BTree items.
            deleted=[]
            for tid, (p, u, d, e, t) in _data.items():
                if tid >= stop: break
                o=[]
                for r in t:
                    c=pindex.get(r[0])
                    if c is None:
                        # GC this record, no longer referenced
                        continue
                    elif c is not r:
                        # This record is not the indexed record,
                        # so it may not be current. Let's see.
                        oid, serial, pre, vdata, p = r
                        if vdata:
                            # Version record are current *only* if they
                            # are indexed
                            continue
                        else:
                            # OK, this isn't a version record, so it may be the
                            # non-version record for the indexed record.
                            oid, serial, pre, vdata, p = c
                            if vdata:
                                if vdata[1] != r:
                                    # This record is not the non-version
                                    # record for the indexed record
                                    continue
                            else:
                                # The indexed record is not a version record,
                                # so this record can not be the non-version
                                # record for it.
                                continue
                    o.append(r)

                if o:
                    if len(o) != len(t):
                        _data[tid]=1, u, d, e, tuple(o) # Reset data
                else:
                    deleted.append(tid)

            # Now delete empty transactions
            for tid in deleted: del _data[tid]

            # Now reset previous pointers for "current" records:
            for r in pindex.values():
                r[2]=None # Previous record
                if r[3]: # vdata
                    r[3][1][2]=None

            pindex=None

            # Finally, rebuild indexes from transaction data:
            self._index, self._vindex = self._build_indexes()

        finally: self._lock_release()
        self.getSize()

    def _splat(self):
        """Spit out a string showing state.
        """
        o=[]

        o.append('Transactions:')
        for tid, (p, u, d, e, t) in self._data.items():
            o.append("  %s %s" % (TimeStamp(tid), p))
            for r in t:
                oid, serial, pre, vdata, p = r
                oid=utils.u64(oid)
                if serial is not None: serial=str(TimeStamp(serial))
                pre=id(pre)
                if vdata and vdata[1]: vdata=vdata[0], id(vdata[1])
                if p: p=''
                o.append('    %s: %s' %
                         (id(r), `(oid, serial, pre, vdata, p)`))

        o.append('\nIndex:')
        items=self._index.items()
        items.sort()
        for oid, r in items:
            if r: r=id(r)
            o.append('  %s: %s' % (utils.u64(oid), r))

        o.append('\nVersion Index:')
        items=self._vindex.items()
        items.sort()
        for version, v in items:
            o.append('  '+version)
            vitems=v.items()
            vitems.sort()
            for oid, r in vitems:
                if r: r=id(r)
                o.append('    %s: %s' % (utils.u64(oid), r))


        return string.join(o,'\n')
