/*****************************************************************************

  Copyright (c) 1996-2002 Zope Corporation and Contributors.
  All Rights Reserved.

  This software is subject to the provisions of the Zope Public License,
  Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
  WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
  WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
  FOR A PARTICULAR PURPOSE

 ****************************************************************************/

static char Missing_module_documentation[] = 
""
"\n$Id: Missing.c,v 1.13.10.1 2002/11/13 16:40:01 jeremy Exp $"
;

#include "ExtensionClass.h"

/* Declarations for objects of type Missing */

typedef struct {
  PyObject_HEAD
} Missing;

static PyObject *vname=0, *Missing_dot_Value=0, *empty_string=0, *reduce=0;
static PyObject *theValue;

static void
Missing_dealloc(Missing *self)
{
  Py_DECREF(self->ob_type);
  PyMem_DEL(self);
}

static PyObject *
Missing_repr(Missing *self)
{
  Py_INCREF(Missing_dot_Value);
  return Missing_dot_Value;
}

static PyObject *
Missing_str(Missing *self)
{
  Py_INCREF(empty_string);
  return empty_string;
}

/* Code to access Missing objects as numbers */

static PyObject *
Missing_bin(PyObject *v, PyObject *w)
{
  Py_INCREF(v);
  return v;
}

static PyObject *
Missing_pow(PyObject *v, PyObject *w, PyObject *z)
{
  Py_INCREF(v);
  return v;
}				

static PyObject *
Missing_un(PyObject *v)
{
  Py_INCREF(v);
  return v;
}

static int
Missing_nonzero(PyObject *v)
{
  return 0;
}

static int
Missing_coerce(PyObject **pv, PyObject **pw)
{
  Py_INCREF(*pv);
  Py_INCREF(*pw);
  return 0;
}

static PyObject *
Missing_int(Missing *v)
{
  PyErr_SetString(PyExc_TypeError,
		  "Missing objects do not support conversion to integer");
  return NULL;
}

static PyObject *
Missing_long(Missing *v)
{
  PyErr_SetString(PyExc_TypeError,
		  "Missing objects do not support conversion to long");
  return NULL;
}

static PyObject *
Missing_float(Missing *v)
{
  PyErr_SetString(PyExc_TypeError,
		  "Missing objects do not support conversion to float");
  return NULL;
}

static PyObject *
Missing_oct(Missing *v)
{ 
  PyErr_SetString(PyExc_TypeError,
	  "Missing objects do not support conversion to an octal string");
  return NULL;
}

static PyObject *
Missing_hex(Missing *v)
{
  PyErr_SetString(PyExc_TypeError,
     	"Missing objects do not support conversion to hexadecimal strings");
  return NULL;
}

static PyNumberMethods Missing_as_number = {
	(binaryfunc)Missing_bin,	/*nb_add*/
	(binaryfunc)Missing_bin,	/*nb_subtract*/
	(binaryfunc)Missing_bin,	/*nb_multiply*/
	(binaryfunc)Missing_bin,	/*nb_divide*/
	(binaryfunc)Missing_bin,	/*nb_remainder*/
	(binaryfunc)Missing_bin,	/*nb_divmod*/
	(ternaryfunc)Missing_pow,	/*nb_power*/
	(unaryfunc)Missing_un,	/*nb_negative*/
	(unaryfunc)Missing_un,	/*nb_positive*/
	(unaryfunc)Missing_un,	/*nb_absolute*/
	(inquiry)Missing_nonzero,	/*nb_nonzero*/
	(unaryfunc)Missing_un,	/*nb_invert*/
	(binaryfunc)Missing_bin,	/*nb_lshift*/
	(binaryfunc)Missing_bin,	/*nb_rshift*/
	(binaryfunc)Missing_bin,	/*nb_and*/
	(binaryfunc)Missing_bin,	/*nb_xor*/
	(binaryfunc)Missing_bin,	/*nb_or*/
	(coercion)Missing_coerce,	/*nb_coerce*/
	(unaryfunc)Missing_int,	/*nb_int*/
	(unaryfunc)Missing_long,	/*nb_long*/
	(unaryfunc)Missing_float,	/*nb_float*/
	(unaryfunc)Missing_oct,	/*nb_oct*/
	(unaryfunc)Missing_hex,	/*nb_hex*/
};

/* ------------------------------------------------------- */

static PyObject *
Missing_reduce(PyObject *self, PyObject *args, PyObject *kw)
{
  if(self==theValue)
    {
      Py_INCREF(vname);
      return vname;
    }
  return Py_BuildValue("O()",self->ob_type);
}

static struct PyMethodDef reduce_ml[] = {  
  {"__reduce__", (PyCFunction)Missing_reduce, 1,
   "Return a missing value reduced to standard python objects"
  }
};

static PyObject *
Missing_getattr(PyObject *self, PyObject *name)
{
  char *c, *legal;

  if(!(c=PyString_AsString(name))) return NULL;

  legal=c;
  if (strchr("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", 
	     *legal) != NULL)
    {
      for (legal++; *legal; legal++)
	if (strchr("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_", 
		   *legal) == NULL) 
	  {
	    legal=NULL;
	    break;
	  }
    }
  else legal=NULL;

  if(! legal)
    {
      if(strcmp(c,"__reduce__")==0)
	{
	  if(self==theValue)
	    {
	      Py_INCREF(reduce);
	      return reduce;
	    }
	  return PyCFunction_New(reduce_ml, self);
	}
      PyErr_SetObject(PyExc_AttributeError, name);
      return NULL;
    }

  Py_INCREF(self);
  return self;
}

static PyObject *
Missing_call(PyObject *self, PyObject *args, PyObject *kw)
{
  Py_INCREF(self);
  return self;
}

static int
Missing_cmp(Missing *m1, Missing *m2)
{
  return m1->ob_type != m2->ob_type ;
}

static PyExtensionClass MissingType = {
  PyObject_HEAD_INIT(NULL)
  0,					/*ob_size*/
  "Missing",				/*tp_name*/
  sizeof(Missing),			/*tp_basicsize*/
  0,					/*tp_itemsize*/
  /* methods */
  (destructor)Missing_dealloc,		/*tp_dealloc*/
  (printfunc)0,				/*tp_print*/
  (getattrfunc)0,			/*obsolete tp_getattr*/
  (setattrfunc)0,			/*obsolete tp_setattr*/
  (cmpfunc)Missing_cmp,			/*tp_compare*/
  (reprfunc)Missing_repr,		/*tp_repr*/
  &Missing_as_number,			/*tp_as_number*/
  0,					/*tp_as_sequence*/
  0,					/*tp_as_mapping*/
  (hashfunc)0,				/*tp_hash*/
  (ternaryfunc)Missing_call,		/*tp_call*/
  (reprfunc)Missing_str,		/*tp_str*/
  (getattrofunc)Missing_getattr,	/*tp_getattro*/
  (setattrofunc)0,			/*tp_setattro*/
  
  /* Space for future expansion */
  0L,0L,
  "Represent totally unknown quantities\n"
  "\n"
  "Missing values are used to represent numberic quantities that are\n"
  "unknown.  They support all mathematical operations except\n"
  "conversions by returning themselves.\n",
  METHOD_CHAIN(NULL)
};

/* End of code for Missing objects */
/* -------------------------------------------------------- */


/* List of methods defined in the module */

static struct PyMethodDef Module_Level__methods[] = {  
  {NULL, (PyCFunction)NULL, 0, NULL}		/* sentinel */
};

void
initMissing(void)
{
  PyObject *m, *d;

  if(! ((vname=PyString_FromString("V"))
	&& (Missing_dot_Value=PyString_FromString("Missing.Value"))
	&& (empty_string=PyString_FromString(""))
	)) return;

  /* Create the module and add the functions */
  m = Py_InitModule4("Missing", Module_Level__methods,
		     Missing_module_documentation,
		     (PyObject*)NULL,PYTHON_API_VERSION);

  /* Add some symbolic constants to the module */
  d = PyModule_GetDict(m);

  PyExtensionClass_Export(d,"Missing",MissingType);

  theValue=PyObject_CallObject((PyObject*)&MissingType, NULL);
  reduce=PyCFunction_New(reduce_ml, theValue);

  PyDict_SetItemString(d, "Value", theValue);
  PyDict_SetItemString(d, "V", theValue); 
  PyDict_SetItemString(d, "MV", theValue); 
	
  /* Check for errors */
  if (PyErr_Occurred())
    Py_FatalError("can't initialize module Missing");
}

/*****************************************************************************
Revision Log:

  $Log: Missing.c,v $
  Revision 1.13.10.1  2002/11/13 16:40:01  jeremy
  Backport: Fix includes before Python.h.

  Revision 1.13  2002/06/10 22:48:46  jeremy
  Update ExtensionClass to ZPL 2.0.

  Revision 1.12  2002/01/25 15:34:06  gvanrossum
  Get rid of __version__, as Jim recommends.  Use $ from docstring instead.

  Revision 1.11  2001/03/28 14:06:51  jeremy
  gcc -Wall cleanup
      - make function decls prototypes
      - remove unreferenced functions

  Revision 1.10  1999/08/25 20:15:29  jim
  Made getattr a bit pickler to prevent getting attributes like "%f5.3".

  Revision 1.9  1999/06/10 20:09:47  jim
  Updated to use new ExtensionClass destructor protocol.

  Revision 1.8  1998/11/17 19:54:33  jim
  new copyright.

  Revision 1.7  1997/10/03 14:43:27  jim
  Fixed comparison bug, again :-(

  Revision 1.6  1997/09/23 16:06:03  jim
  Added MV member.

  Revision 1.5  1997/09/23 15:17:12  jim
  Added cmp.

  Revision 1.4  1997/09/18 21:01:33  jim
  Added check to getattr to fail on methods that begin with underscore.
  Note that Missing really defeats testing from protocols by testing for
  attributes.

  Revision 1.3  1997/09/17 22:49:35  jim
  Fixed refcount bug.
  Added logic so:  Missing.Value.spam() returns Missing.Value.
  Added logic to make Missing.Value picklable.

  Revision 1.2  1997/07/02 20:19:37  jim
  Got rid of unused macros and ErrorObject.

  Revision 1.1  1997/07/01 21:36:34  jim


*****************************************************************************/
