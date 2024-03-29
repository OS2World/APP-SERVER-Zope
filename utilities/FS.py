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

import struct, tempfile, string, time, pickle, os, sys
from struct import pack, unpack
from cStringIO import StringIO

class FS:
    """FileStorage 'report' writer for converting BoboPOS to FileStorage
    """


    def __init__(self, fname, file):
        file.seek(0,2)
        self._input_size=file.tell()
        file.seek(0)
        self.__name__=fname
        self._file=open(fname,'w+b')
        self._file.write('FS21')

        self._index={}
        self._indexpos=self._index.get
        self._tindex=[]
        self._tappend=self._tindex.append
        self._tfile=tempfile.TemporaryFile()
        self._pos=4
        self._progress=None


    def rpt(self, pos, oid, start, tname, user, t, p, first, newtrans):
        if pos is None:
            self.tpc_finish()
            sys.stderr.write(' %% 100     \n')
            return
        else:
            progress=' %% %.1f \r' % (pos*100.0/self._input_size)
            if progress != self._progress:
                sys.stderr.write(progress)
                self._progress=progress

        if newtrans:
            try: string.atof(tname)
            except:
                # Ugh, we have a weird tname.  We'll just ignore the transaction
                # boundary and merge transactions
                if first:
                    # But we can't ignore the first one, so we'll hack in a
                    # bogus start date
                    self.tpc_begin('100', user, t)
            else:
                if not first: self.tpc_finish()
                self.tpc_begin(tname, user, t)
        self.store(oid, p)

    def store(self, oid, data):
        old=self._indexpos(oid, 0)
        pnv=None

        tfile=self._tfile
        write=tfile.write
        pos=self._pos
        here=tfile.tell()+pos+self._thl
        self._tappend(oid, here)
        serial=self._serial
        data=fixpickle(data, oid)
        write(pack(">8s8s8s8sH8s",
                   p64(oid+1),serial,p64(old),p64(pos),
                   0,p64(len(data))
                   )
              )

        write(data)

    def tpc_begin(self, tname, user, desc):
        del self._tindex[:]   # Just to be sure!
        self._tfile.seek(0)

        t=string.atof(tname)
        y,m,d,h,mi=time.gmtime(t)[:5]
        s=t%60
        self._serial=struct.pack(
            ">II",
            (((((y-1900)*12)+m-1)*31+d-1)*24+h)*60+mi,
            long(s * (1L << 32) / 60)
            )

        # Ugh, we have to record the transaction header length
        # so that we can get version pointers right.
        self._thl=23+len(user)+len(desc)

        # And we have to save the data used to compute the
        # header length. It's unlikely that this stuff would
        # change, but if it did, it would be a disaster.
        self._ud=user, desc

    def tpc_finish(self):
        file=self._file
        write=file.write
        tfile=self._tfile
        dlen=tfile.tell()
        tfile.seek(0)
        id=self._serial
        user, desc = self._ud
        self._ud=None

        tlen=self._thl
        pos=self._pos
        tl=tlen+dlen
        stl=p64(tl)
        write(pack(
            ">8s" "8s" "c"  "H"        "H"        "H"
            ,id, stl, ' ', len(user), len(desc), 0,
            ))
        if user: write(user)
        if desc: write(desc)

        cp(tfile, file, dlen)

        write(stl)
        self._pos=pos+tl+8

        tindex=self._tindex
        index=self._index
        for oid, pos in tindex: index[oid]=pos
        del tindex[:]


class ZEXP:
    """Zope Export format 'report' writer
    """
    def __init__(self, fname, file):
        file.seek(0,2)
        self._input_size=file.tell()
        file.seek(0)
        self.__name__=fname
        self._file=open(fname,'w+b')
        self._file.write('ZEXP')

        self._pos=4
        self._progress=None


    def rpt(self, pos, oid, start, tname, user, t, p, first, newtrans):
        write=self._file.write
        if pos is None:
            write('\377'*16) # end marker
            sys.stderr.write(' %% 100     \n')
            return
        else:
            progress=' %% %.1f \r' % (pos*100.0/self._input_size)
            if progress != self._progress:
                sys.stderr.write(progress)
                self._progress=progress

        data=fixpickle(p, oid)
        l=len(data)
        write(p64(oid+1)+p64(l))
        write(data)
        self._pos=self._pos+l+16


t32 = 1L << 32

def p64(v, pack=struct.pack):
    if v < t32: h=0
    else:
        h=v/t32
        v=v%t32
    return pack(">II", h, v)

def cp(f1, f2, l):
    read=f1.read
    write=f2.write
    n=8192

    while l > 0:
        if n > l: n=l
        d=read(n)
        write(d)
        l = l - len(d)


class Ghost: pass

class Global:
    __safe_for_unpickling__=1

    def __init__(self, m, n):
        self._module, self._name = m, n

    def __call__(self, *args):
        return Inst(self, args)

    def __basicnew__(self):
        return Inst(self, None)

def _global(m, n):
    if m[:8]=='BoboPOS.':
        if m=='BoboPOS.PickleDictionary' and n=='Root':
            m='ZODB.conversionhack'
            n='hack'
        elif m=='BoboPOS.PersistentMapping': m='Persistence'
        elif m=='BoboPOS.cPickleJar' and n=='ec':
            m=n='ExtensionClass'
        else:
            raise 'Unexpected BoboPOS class', (m, n)
    elif m=='PersistentMapping': m='Persistence'

    return Global(m,n)


class Inst:

    _state=None

    def __init__(self, c, args):
        self._cls=c
        self._args=args

    def __setstate__(self, state): self._state=state


from pickle import INST, GLOBAL, MARK, BUILD, OBJ, REDUCE

InstanceType=type(Ghost())

class Unpickler(pickle.Unpickler):

    dispatch={}
    dispatch.update(pickle.Unpickler.dispatch)

    def load_inst(self):
        k = self.marker()
        args = tuple(self.stack[k+1:])
        del self.stack[k:]
        module = self.readline()[:-1]
        name = self.readline()[:-1]
        klass = _global(module, name)
        value=Inst(klass, args)
        self.append(value)

    dispatch[INST] = load_inst

    def load_global(self):
        module = self.readline()[:-1]
        name = self.readline()[:-1]
        klass = _global(module, name)
        self.append(klass)
    dispatch[GLOBAL] = load_global

    def persistent_load(self, oid,
                        TupleType=type(()), Ghost=Ghost, p64=p64):
        "Remap object ids from ZODB 2 stype to ZODB 3 style"

        if type(oid) is TupleType:
            oid, klass = oid
            oid = p64(oid+1), klass
        else:
            oid = p64(oid+1)

        Ghost=Ghost()
        Ghost.oid=oid
        return Ghost


class Pickler(pickle.Pickler):

    dispatch={}
    dispatch.update(pickle.Pickler.dispatch)

    def persistent_id(self, object, Ghost=Ghost):
        if hasattr(object, '__class__') and object.__class__ is Ghost:
            return object.oid

    def save_inst(self, object):
        d = id(object)
        cls = object.__class__

        memo  = self.memo
        write = self.write
        save  = self.save

        if cls is Global:
            memo_len = len(memo)
            write(GLOBAL + object._module + '\n' + object._name + '\n' +
                  self.put(memo_len))
            memo[d] = (memo_len, object)
            return

        self.save_inst(object._cls)
        save(object._args)

        memo_len = len(memo)
        write(REDUCE + self.put(memo_len))

        memo[d] = (memo_len, object)

        stuff=object._state
        save(stuff)
        write(BUILD)

    dispatch[InstanceType] = save_inst

    def save_global(self, object, name = None):
        write = self.write
        memo = self.memo

        if (name is None):
            name = object._name

        module=object._module

        memo_len = len(memo)
        write(GLOBAL + module + '\n' + name + '\n' +
            self.put(memo_len))
        memo[id(object)] = (memo_len, object)

    dispatch[type(Ghost)] = save_global


def fixpickle(p, oid):

    pfile=StringIO(p)
    unpickler=Unpickler(pfile)

    newp=StringIO()
    pickler=Pickler(newp,1)

    pickler.dump(unpickler.load())
    state=unpickler.load()
    if oid==-1: state={'_container': state}
    pickler.dump(state)
    p=newp.getvalue()

    return p
