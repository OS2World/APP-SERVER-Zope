/*****************************************************************************

  Copyright (c) 2001, 2002 Zope Corporation and Contributors.
  All Rights Reserved.

  This software is subject to the provisions of the Zope Public License,
  Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
  WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
  WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
  FOR A PARTICULAR PURPOSE

 ****************************************************************************/

#define BTREEITEMSTEMPLATE_C "$Id: BTreeItemsTemplate.c,v 1.17 2002/06/22 17:22:54 tim_one Exp $\n"

/* A BTreeItems struct is returned from calling .items(), .keys() or
 * .values() on a BTree-based data structure, and is also the result of
 * taking slices of those.  It represents a contiguous slice of a BTree.
 *
 * The start of the slice is in firstbucket, at offset first.  The end of
 * the slice is in lastbucket, at offset last.  Both endpoints are inclusive.
 * It must possible to get from firstbucket to lastbucket via following
 * bucket 'next' pointers zero or more times.  firstbucket, first, lastbucket,
 * and last are readonly after initialization.  An empty slice is represented
 * by  firstbucket == lastbucket == currentbucket == NULL.
 *
 * 'kind' determines whether this slice represents 'k'eys alone, 'v'alues
 * alone, or 'i'items (key+value pairs).  'kind' is also readonly after
 * initialization.
 *
 * The combination of currentbucket, currentoffset and pseudoindex acts as
 * a search finger.  Offset currentoffset in bucket currentbucket is at index
 * pseudoindex, where pseudoindex==0 corresponds to offset first in bucket
 * firstbucket, and pseudoindex==-1 corresponds to offset last in bucket
 * lastbucket.  The function BTreeItems_seek() can be used to set this combo
 * correctly for any in-bounds index, and uses this combo on input to avoid
 * needing to search from the start (or end) on each call.  Calling
 * BTreeItems_seek() with consecutive larger positions is very efficent.
 * Calling it with consecutive smaller positions is more efficient than if
 * a search finger weren't being used at all, but is still quadratic time
 * in the number of buckets in the slice.
 */
typedef struct {
  PyObject_HEAD
  Bucket *firstbucket;		/* First bucket		          */
  Bucket *currentbucket;	/* Current bucket (search finger) */
  Bucket *lastbucket;		/* Last bucket		          */
  int currentoffset;		/* Offset in currentbucket        */
  int pseudoindex;		/* search finger index            */
  int first;                    /* Start offset in firstbucket    */
  int last;                     /* End offset in lastbucket       */
  char kind;                    /* 'k', 'v', 'i'                  */
} BTreeItems;

#define ITEMS(O)((BTreeItems*)(O))

static PyObject *
newBTreeItems(char kind,
              Bucket *lowbucket, int lowoffset,
              Bucket *highbucket, int highoffset);

static void
BTreeItems_dealloc(BTreeItems *self)
{
  Py_XDECREF(self->firstbucket);
  Py_XDECREF(self->lastbucket);
  Py_XDECREF(self->currentbucket);
  PyObject_DEL(self);
}

static int
BTreeItems_length_or_nonzero(BTreeItems *self, int nonzero)
{
  int r;
  Bucket *b, *next;

  b=self->firstbucket;
  UNLESS(b) return 0;

  r=self->last + 1 - self->first;

  if (nonzero && r > 0)
    /* Short-circuit if all we care about is nonempty */
    return 1;

  if (b == self->lastbucket) return r;

  Py_INCREF(b);
  PER_USE_OR_RETURN(b, -1);
  while ((next=b->next))
    {
      r += b->len;
      if (nonzero && r > 0)
        /* Short-circuit if all we care about is nonempty */
        break;

      if (next == self->lastbucket)
        break; /* we already counted the last bucket */

      Py_INCREF(next);
      PER_ALLOW_DEACTIVATION(b);
      PER_ACCESSED(b);
      Py_DECREF(b);
      b=next;
      PER_USE_OR_RETURN(b, -1);
    }
  PER_ALLOW_DEACTIVATION(b);
  PER_ACCESSED(b);
  Py_DECREF(b);

  return r >= 0 ? r : 0;
}

static int
BTreeItems_length( BTreeItems *self)
{
  return BTreeItems_length_or_nonzero(self, 0);
}

/*
** BTreeItems_seek
**
** Find the ith position in the BTreeItems.
**
** Arguments:  	self	The BTree
**		i	the index to seek to, in 0 .. len(self)-1, or in
**                      -len(self) .. -1, as for indexing a Python sequence.
**
**
** Returns 0 if successful, -1 on failure to seek (like out-of-bounds).
** Upon successful return, index i is at offset self->currentoffset in bucket
** self->currentbucket.
*/
static int
BTreeItems_seek(BTreeItems *self, int i)
{
    int delta, pseudoindex, currentoffset;
    Bucket *b, *currentbucket;

    pseudoindex = self->pseudoindex;
    currentoffset = self->currentoffset;
    currentbucket = self->currentbucket;
    if (currentbucket == NULL) goto no_match;

    /* Make sure that the index and pseudoindex have the same sign. */
    if (pseudoindex < 0 && i >= 0) {
        /* Position to the start of the sequence. */
        currentbucket = self->firstbucket;
        currentoffset = self->first;
        pseudoindex = 0;
    }
    else if (pseudoindex >= 0 && i < 0) {
        /* Position to the end of the sequence. */
        currentbucket = self->lastbucket;
        currentoffset = self->last;
        pseudoindex = -1;
    }

    delta = i - pseudoindex;
    while (delta > 0) {         /* move right */
        int max;
        /* Want to move right delta positions; the most we can move right in
         * this bucket is currentbucket->len - currentoffset - 1 positions.
         */
        PER_USE_OR_RETURN(currentbucket, -1);
        max = currentbucket->len - currentoffset - 1;
        b = currentbucket->next;
        PER_ALLOW_DEACTIVATION(currentbucket);
        PER_ACCESSED(currentbucket);
        if (delta <= max) {
            currentoffset += delta;
            pseudoindex += delta;
            if (currentbucket == self->lastbucket
                && currentoffset > self->last) goto no_match;
            break;
        }
        /* Move to start of next bucket. */
        if (currentbucket == self->lastbucket || b == NULL) goto no_match;
        currentbucket = b;
        pseudoindex += max + 1;
        delta -= max + 1;
        currentoffset = 0;
    }
    while (delta < 0) {         /* move left */
        int status;
        /* Want to move left -delta positions; the most we can move left in
         * this bucket is currentoffset positions.
         */
        if ((-delta) <= currentoffset) {
            currentoffset += delta;
            pseudoindex += delta;
            if (currentbucket == self->firstbucket
                && currentoffset < self->first) goto no_match;
            break;
        }
        /* Move to end of previous bucket. */
        if (currentbucket == self->firstbucket) goto no_match;
        status = PreviousBucket(&currentbucket, self->firstbucket);
        if (status == 0)
            goto no_match;
        else if (status < 0)
            return -1;
        pseudoindex -= currentoffset + 1;
        delta += currentoffset + 1;
        PER_USE_OR_RETURN(currentbucket, -1);
        currentoffset = currentbucket->len - 1;
        PER_ALLOW_DEACTIVATION(currentbucket);
        PER_ACCESSED(currentbucket);
    }

    assert(pseudoindex == i);
    Py_INCREF(currentbucket);
    Py_DECREF(self->currentbucket);
    self->currentbucket = currentbucket;
    self->currentoffset = currentoffset;
    self->pseudoindex = pseudoindex;
    return 0;

no_match:
    IndexError(i);
    return -1;
}

/*
** BTreeItems_item
**
** Arguments:	self	a BTreeItems structure
**		i	Which item to inspect
**
** Returns:	the BTreeItems_item_BTree of self->kind, i
**		(ie pulls the ith item out)
*/
static PyObject *
BTreeItems_item(BTreeItems *self, int i)
{
  PyObject *r, *k=0, *v=0;

  if (BTreeItems_seek(self, i) < 0) return NULL;

  PER_USE_OR_RETURN(self->currentbucket, NULL);

  switch(self->kind) {

  case 'v':
    COPY_VALUE_TO_OBJECT(r, self->currentbucket->values[self->currentoffset]);
    break;

  case 'i':
    COPY_KEY_TO_OBJECT(k, self->currentbucket->keys[self->currentoffset]);
    UNLESS (k) return NULL;

    COPY_VALUE_TO_OBJECT(v, self->currentbucket->values[self->currentoffset]);
    UNLESS (v) return NULL;

    UNLESS (r=PyTuple_New(2)) goto err;

    PyTuple_SET_ITEM(r, 0, k);
    PyTuple_SET_ITEM(r, 1, v);
    break;

  default:
    COPY_KEY_TO_OBJECT(r, self->currentbucket->keys[self->currentoffset]);
    break;
  }

  PER_UNUSE(self->currentbucket);
  return r;

 err:
  Py_DECREF(k);
  Py_XDECREF(v);
  PER_UNUSE(self->currentbucket);
  return NULL;
}

/*
** BTreeItems_slice
**
** Creates a new BTreeItems structure representing the slice
** between the low and high range
**
** Arguments:	self	The old BTreeItems structure
**		ilow	The start index
**		ihigh	The end index
**
** Returns:	BTreeItems item
*/
static PyObject *
BTreeItems_slice(BTreeItems *self, int ilow, int ihigh)
{
  Bucket *lowbucket;
  Bucket *highbucket;
  int lowoffset;
  int highoffset;
  int length = -1;  /* len(self), but computed only if needed */

  /* Complications:
   * A Python slice never raises IndexError, but BTreeItems_seek does.
   * Python did only part of index normalization before calling this:
   *     ilow may be < 0 now, and ihigh may be arbitrarily large.  It's
   *     our responsibility to clip them.
   * A Python slice is exclusive of the high index, but a BTreeItems
   *     struct is inclusive on both ends.
   */

  /* First adjust ilow and ihigh to be legit endpoints in the Python
   * sense (ilow inclusive, ihigh exclusive).  This block duplicates the
   * logic from Python's list_slice function (slicing for builtin lists).
   */
  if (ilow < 0)
      ilow = 0;
  else {
      if (length < 0)
          length = BTreeItems_length(self);
      if (ilow > length)
          ilow = length;
  }

  if (ihigh < ilow)
      ihigh = ilow;
  else {
      if (length < 0)
          length = BTreeItems_length(self);
      if (ihigh > length)
          ihigh = length;
  }
  assert(0 <= ilow && ilow <= ihigh);
  assert(length < 0 || ihigh <= length);

  /* Now adjust for that our struct is inclusive on both ends.  This is
   * easy *except* when the slice is empty:  there's no good way to spell
   * that in an inclusive-on-both-ends scheme.  For example, if the
   * slice is btree.items([:0]), ilow == ihigh == 0 at this point, and if
   * we were to subtract 1 from ihigh that would get interpreted by
   * BTreeItems_seek as meaning the *entire* set of items.  Setting ilow==1
   * and ihigh==0 doesn't work either, as BTreeItems_seek raises IndexError
   * if we attempt to seek to ilow==1 when the underlying sequence is empty.
   * It seems simplest to deal with empty slices as a special case here.
   */
   if (ilow == ihigh) {
       /* empty slice */
       lowbucket = highbucket = NULL;
       lowoffset = 1;
       highoffset = 0;
   }
   else {
       assert(ilow < ihigh);
       --ihigh;  /* exclusive -> inclusive */

       if (BTreeItems_seek(self, ilow) < 0) return NULL;
       lowbucket = self->currentbucket;
       lowoffset = self->currentoffset;

       if (BTreeItems_seek(self, ihigh) < 0) return NULL;

       highbucket = self->currentbucket;
       highoffset = self->currentoffset;
  }
  return newBTreeItems(self->kind,
                       lowbucket, lowoffset, highbucket, highoffset);
}

static PySequenceMethods BTreeItems_as_sequence = {
  (inquiry) BTreeItems_length,
  (binaryfunc)0,
  (intargfunc)0,
  (intargfunc) BTreeItems_item,
  (intintargfunc) BTreeItems_slice,
};

/* Number Method items (just for nb_nonzero!) */

static int
BTreeItems_nonzero(BTreeItems *self)
{
  return BTreeItems_length_or_nonzero(self, 1);
}

static PyNumberMethods BTreeItems_as_number_for_nonzero = {
  0,0,0,0,0,0,0,0,0,0,
   (inquiry)BTreeItems_nonzero};

static PyTypeObject BTreeItemsType = {
  PyObject_HEAD_INIT(NULL)
  0,					/*ob_size*/
  MOD_NAME_PREFIX "BTreeItems",	        /*tp_name*/
  sizeof(BTreeItems),		        /*tp_basicsize*/
  0,					/*tp_itemsize*/
  /* methods */
  (destructor) BTreeItems_dealloc,	/*tp_dealloc*/
  (printfunc)0,				/*tp_print*/
  (getattrfunc)0,			/*obsolete tp_getattr*/
  (setattrfunc)0,			/*obsolete tp_setattr*/
  (cmpfunc)0,				/*tp_compare*/
  (reprfunc)0,				/*tp_repr*/
  &BTreeItems_as_number_for_nonzero,	/*tp_as_number*/
  &BTreeItems_as_sequence,		/*tp_as_sequence*/
  0,					/*tp_as_mapping*/
  (hashfunc)0,				/*tp_hash*/
  (ternaryfunc)0,			/*tp_call*/
  (reprfunc)0,				/*tp_str*/
  0,					/*tp_getattro*/
  0,					/*tp_setattro*/

  /* Space for future expansion */
  0L,0L,
  "Sequence type used to iterate over BTree items." /* Documentation string */
};

/* Returns a new BTreeItems object representing the contiguous slice from
 * offset lowoffset in bucket lowbucket through offset highoffset in bucket
 * highbucket, inclusive.  Pass lowbucket == NULL for an empty slice.
 * The currentbucket is set to lowbucket, currentoffset ot lowoffset, and
 * pseudoindex to 0.  kind is 'k', 'v' or 'i' (see BTreeItems struct docs).
 */
static PyObject *
newBTreeItems(char kind,
              Bucket *lowbucket, int lowoffset,
              Bucket *highbucket, int highoffset)
{
  BTreeItems *self;

  UNLESS (self = PyObject_NEW(BTreeItems, &BTreeItemsType)) return NULL;
  self->kind = kind;

  self->first = lowoffset;
  self->last = highoffset;

  if (! lowbucket || ! highbucket
      || (lowbucket == highbucket && lowoffset > highoffset))
    {
      self->firstbucket   = 0;
      self->lastbucket    = 0;
      self->currentbucket = 0;
    }
  else
    {
      Py_INCREF(lowbucket);
      self->firstbucket = lowbucket;
      Py_XINCREF(highbucket);
      self->lastbucket = highbucket;
      Py_XINCREF(lowbucket);
      self->currentbucket = lowbucket;
    }

  self->currentoffset = lowoffset;
  self->pseudoindex = 0;

  return OBJECT(self);
}

static int
nextBTreeItems(SetIteration *i)
{
  if (i->position >= 0)
    {
      if (i->position)
        {
          DECREF_KEY(i->key);
          DECREF_VALUE(i->value);
        }

      if (BTreeItems_seek(ITEMS(i->set), i->position) >= 0)
        {
          Bucket *currentbucket;

          currentbucket = BUCKET(ITEMS(i->set)->currentbucket);
          UNLESS(PER_USE(currentbucket))
            {
              /* Mark iteration terminated, so that finiSetIteration doesn't
               * try to redundantly decref the key and value
               */
              i->position = -1;
              return -1;
            }

          COPY_KEY(i->key, currentbucket->keys[ITEMS(i->set)->currentoffset]);
          INCREF_KEY(i->key);

          COPY_VALUE(i->value,
                     currentbucket->values[ITEMS(i->set)->currentoffset]);
          COPY_VALUE(i->value,
                   BUCKET(ITEMS(i->set)->currentbucket)
                   ->values[ITEMS(i->set)->currentoffset]);
          INCREF_VALUE(i->value);

          i->position ++;

          PER_UNUSE(currentbucket);
        }
      else
        {
          i->position = -1;
          PyErr_Clear();
        }
    }
  return 0;
}

static int
nextTreeSetItems(SetIteration *i)
{
  if (i->position >= 0)
    {
      if (i->position)
        {
          DECREF_KEY(i->key);
        }

      if (BTreeItems_seek(ITEMS(i->set), i->position) >= 0)
        {
          Bucket *currentbucket;

          currentbucket = BUCKET(ITEMS(i->set)->currentbucket);
          UNLESS(PER_USE(currentbucket))
            {
              /* Mark iteration terminated, so that finiSetIteration doesn't
               * try to redundantly decref the key and value
               */
              i->position = -1;
              return -1;
            }

          COPY_KEY(i->key, currentbucket->keys[ITEMS(i->set)->currentoffset]);
          INCREF_KEY(i->key);

          i->position ++;

          PER_UNUSE(currentbucket);
        }
      else
        {
          i->position = -1;
          PyErr_Clear();
        }
    }
  return 0;
}
