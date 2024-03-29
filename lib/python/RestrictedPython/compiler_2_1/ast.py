"""Python abstract syntax node definitions

This file is automatically generated.
"""
from types import TupleType, ListType
from consts import CO_VARARGS, CO_VARKEYWORDS

def flatten(list):
    l = []
    for elt in list:
        t = type(elt)
        if t is TupleType or t is ListType:
            for elt2 in flatten(elt):
                l.append(elt2)
        else:
            l.append(elt)
    return l

def asList(nodes):
    l = []
    for item in nodes:
        if hasattr(item, "asList"):
            l.append(item.asList())
        else:
            t = type(item)
            if t is TupleType or t is ListType:
                l.append(tuple(asList(item)))
            else:
                l.append(item)
    return l

nodes = {}

class Node:
    lineno = None
    def getType(self):
        pass
    def getChildren(self):
        # XXX It would be better to generate flat values to begin with
        return flatten(self._getChildren())
    def asList(self):
        return tuple(asList(self.getChildren()))

class EmptyNode(Node):
    def __init__(self):
        self.lineno = None

class If(Node):
    nodes["if"] = "If"
    def __init__(self, tests, else_):
        self.tests = tests
        self.else_ = else_
    def _getChildren(self):
        return self.tests, self.else_
    def __repr__(self):
        return "If(%s, %s)" % (repr(self.tests), repr(self.else_))

class ListComp(Node):
    nodes["listcomp"] = "ListComp"
    def __init__(self, expr, quals):
        self.expr = expr
        self.quals = quals
    def _getChildren(self):
        return self.expr, self.quals
    def __repr__(self):
        return "ListComp(%s, %s)" % (repr(self.expr), repr(self.quals))

class Bitor(Node):
    nodes["bitor"] = "Bitor"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "Bitor(%s)" % (repr(self.nodes),)

class Pass(Node):
    nodes["pass"] = "Pass"
    def __init__(self, ):
        pass
    def _getChildren(self):
        return ()
    def __repr__(self):
        return "Pass()"

class Module(Node):
    nodes["module"] = "Module"
    def __init__(self, doc, node):
        self.doc = doc
        self.node = node
    def _getChildren(self):
        return self.doc, self.node
    def __repr__(self):
        return "Module(%s, %s)" % (repr(self.doc), repr(self.node))

class Global(Node):
    nodes["global"] = "Global"
    def __init__(self, names):
        self.names = names
    def _getChildren(self):
        return self.names,
    def __repr__(self):
        return "Global(%s)" % (repr(self.names),)

class CallFunc(Node):
    nodes["callfunc"] = "CallFunc"
    def __init__(self, node, args, star_args = None, dstar_args = None):
        self.node = node
        self.args = args
        self.star_args = star_args
        self.dstar_args = dstar_args
    def _getChildren(self):
        return self.node, self.args, self.star_args, self.dstar_args
    def __repr__(self):
        return "CallFunc(%s, %s, %s, %s)" % (repr(self.node), repr(self.args), repr(self.star_args), repr(self.dstar_args))

class Printnl(Node):
    nodes["printnl"] = "Printnl"
    def __init__(self, nodes, dest):
        self.nodes = nodes
        self.dest = dest
    def _getChildren(self):
        return self.nodes, self.dest
    def __repr__(self):
        return "Printnl(%s, %s)" % (repr(self.nodes), repr(self.dest))

class Tuple(Node):
    nodes["tuple"] = "Tuple"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "Tuple(%s)" % (repr(self.nodes),)

class Compare(Node):
    nodes["compare"] = "Compare"
    def __init__(self, expr, ops):
        self.expr = expr
        self.ops = ops
    def _getChildren(self):
        return self.expr, self.ops
    def __repr__(self):
        return "Compare(%s, %s)" % (repr(self.expr), repr(self.ops))

class And(Node):
    nodes["and"] = "And"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "And(%s)" % (repr(self.nodes),)

class Lambda(Node):
    nodes["lambda"] = "Lambda"
    def __init__(self, argnames, defaults, flags, code):
        self.argnames = argnames
        self.defaults = defaults
        self.flags = flags
        self.code = code
        self.varargs = self.kwargs = None
        if flags & CO_VARARGS:
            self.varargs = 1
        if flags & CO_VARKEYWORDS:
            self.kwargs = 1

    def _getChildren(self):
        return self.argnames, self.defaults, self.flags, self.code
    def __repr__(self):
        return "Lambda(%s, %s, %s, %s)" % (repr(self.argnames), repr(self.defaults), repr(self.flags), repr(self.code))

class Assign(Node):
    nodes["assign"] = "Assign"
    def __init__(self, nodes, expr):
        self.nodes = nodes
        self.expr = expr
    def _getChildren(self):
        return self.nodes, self.expr
    def __repr__(self):
        return "Assign(%s, %s)" % (repr(self.nodes), repr(self.expr))

class Sub(Node):
    nodes["sub"] = "Sub"
    def __init__(self, (left, right)):
        self.left = left
        self.right = right
    def _getChildren(self):
        return self.left, self.right
    def __repr__(self):
        return "Sub(%s, %s)" % (repr(self.left), repr(self.right))

class ListCompIf(Node):
    nodes["listcompif"] = "ListCompIf"
    def __init__(self, test):
        self.test = test
    def _getChildren(self):
        return self.test,
    def __repr__(self):
        return "ListCompIf(%s)" % (repr(self.test),)

class Div(Node):
    nodes["div"] = "Div"
    def __init__(self, (left, right)):
        self.left = left
        self.right = right
    def _getChildren(self):
        return self.left, self.right
    def __repr__(self):
        return "Div(%s, %s)" % (repr(self.left), repr(self.right))

class Discard(Node):
    nodes["discard"] = "Discard"
    def __init__(self, expr):
        self.expr = expr
    def _getChildren(self):
        return self.expr,
    def __repr__(self):
        return "Discard(%s)" % (repr(self.expr),)

class Backquote(Node):
    nodes["backquote"] = "Backquote"
    def __init__(self, expr):
        self.expr = expr
    def _getChildren(self):
        return self.expr,
    def __repr__(self):
        return "Backquote(%s)" % (repr(self.expr),)

class RightShift(Node):
    nodes["rightshift"] = "RightShift"
    def __init__(self, (left, right)):
        self.left = left
        self.right = right
    def _getChildren(self):
        return self.left, self.right
    def __repr__(self):
        return "RightShift(%s, %s)" % (repr(self.left), repr(self.right))

class Continue(Node):
    nodes["continue"] = "Continue"
    def __init__(self, ):
        pass
    def _getChildren(self):
        return ()
    def __repr__(self):
        return "Continue()"

class While(Node):
    nodes["while"] = "While"
    def __init__(self, test, body, else_):
        self.test = test
        self.body = body
        self.else_ = else_
    def _getChildren(self):
        return self.test, self.body, self.else_
    def __repr__(self):
        return "While(%s, %s, %s)" % (repr(self.test), repr(self.body), repr(self.else_))

class AssName(Node):
    nodes["assname"] = "AssName"
    def __init__(self, name, flags):
        self.name = name
        self.flags = flags
    def _getChildren(self):
        return self.name, self.flags
    def __repr__(self):
        return "AssName(%s, %s)" % (repr(self.name), repr(self.flags))

class LeftShift(Node):
    nodes["leftshift"] = "LeftShift"
    def __init__(self, (left, right)):
        self.left = left
        self.right = right
    def _getChildren(self):
        return self.left, self.right
    def __repr__(self):
        return "LeftShift(%s, %s)" % (repr(self.left), repr(self.right))

class Mul(Node):
    nodes["mul"] = "Mul"
    def __init__(self, (left, right)):
        self.left = left
        self.right = right
    def _getChildren(self):
        return self.left, self.right
    def __repr__(self):
        return "Mul(%s, %s)" % (repr(self.left), repr(self.right))

class List(Node):
    nodes["list"] = "List"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "List(%s)" % (repr(self.nodes),)

class AugAssign(Node):
    nodes["augassign"] = "AugAssign"
    def __init__(self, node, op, expr):
        self.node = node
        self.op = op
        self.expr = expr
    def _getChildren(self):
        return self.node, self.op, self.expr
    def __repr__(self):
        return "AugAssign(%s, %s, %s)" % (repr(self.node), repr(self.op), repr(self.expr))

class Or(Node):
    nodes["or"] = "Or"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "Or(%s)" % (repr(self.nodes),)

class Keyword(Node):
    nodes["keyword"] = "Keyword"
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr
    def _getChildren(self):
        return self.name, self.expr
    def __repr__(self):
        return "Keyword(%s, %s)" % (repr(self.name), repr(self.expr))

class AssAttr(Node):
    nodes["assattr"] = "AssAttr"
    def __init__(self, expr, attrname, flags):
        self.expr = expr
        self.attrname = attrname
        self.flags = flags
    def _getChildren(self):
        return self.expr, self.attrname, self.flags
    def __repr__(self):
        return "AssAttr(%s, %s, %s)" % (repr(self.expr), repr(self.attrname), repr(self.flags))

class Const(Node):
    nodes["const"] = "Const"
    def __init__(self, value):
        self.value = value
    def _getChildren(self):
        return self.value,
    def __repr__(self):
        return "Const(%s)" % (repr(self.value),)

class Mod(Node):
    nodes["mod"] = "Mod"
    def __init__(self, (left, right)):
        self.left = left
        self.right = right
    def _getChildren(self):
        return self.left, self.right
    def __repr__(self):
        return "Mod(%s, %s)" % (repr(self.left), repr(self.right))

class Class(Node):
    nodes["class"] = "Class"
    def __init__(self, name, bases, doc, code):
        self.name = name
        self.bases = bases
        self.doc = doc
        self.code = code
    def _getChildren(self):
        return self.name, self.bases, self.doc, self.code
    def __repr__(self):
        return "Class(%s, %s, %s, %s)" % (repr(self.name), repr(self.bases), repr(self.doc), repr(self.code))

class Not(Node):
    nodes["not"] = "Not"
    def __init__(self, expr):
        self.expr = expr
    def _getChildren(self):
        return self.expr,
    def __repr__(self):
        return "Not(%s)" % (repr(self.expr),)

class Bitxor(Node):
    nodes["bitxor"] = "Bitxor"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "Bitxor(%s)" % (repr(self.nodes),)

class TryFinally(Node):
    nodes["tryfinally"] = "TryFinally"
    def __init__(self, body, final):
        self.body = body
        self.final = final
    def _getChildren(self):
        return self.body, self.final
    def __repr__(self):
        return "TryFinally(%s, %s)" % (repr(self.body), repr(self.final))

class Bitand(Node):
    nodes["bitand"] = "Bitand"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "Bitand(%s)" % (repr(self.nodes),)

class Break(Node):
    nodes["break"] = "Break"
    def __init__(self, ):
        pass
    def _getChildren(self):
        return ()
    def __repr__(self):
        return "Break()"

class Stmt(Node):
    nodes["stmt"] = "Stmt"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "Stmt(%s)" % (repr(self.nodes),)

class Assert(Node):
    nodes["assert"] = "Assert"
    def __init__(self, test, fail):
        self.test = test
        self.fail = fail
    def _getChildren(self):
        return self.test, self.fail
    def __repr__(self):
        return "Assert(%s, %s)" % (repr(self.test), repr(self.fail))

class Exec(Node):
    nodes["exec"] = "Exec"
    def __init__(self, expr, locals, globals):
        self.expr = expr
        self.locals = locals
        self.globals = globals
    def _getChildren(self):
        return self.expr, self.locals, self.globals
    def __repr__(self):
        return "Exec(%s, %s, %s)" % (repr(self.expr), repr(self.locals), repr(self.globals))

class Power(Node):
    nodes["power"] = "Power"
    def __init__(self, (left, right)):
        self.left = left
        self.right = right
    def _getChildren(self):
        return self.left, self.right
    def __repr__(self):
        return "Power(%s, %s)" % (repr(self.left), repr(self.right))

class Import(Node):
    nodes["import"] = "Import"
    def __init__(self, names):
        self.names = names
    def _getChildren(self):
        return self.names,
    def __repr__(self):
        return "Import(%s)" % (repr(self.names),)

class Return(Node):
    nodes["return"] = "Return"
    def __init__(self, value):
        self.value = value
    def _getChildren(self):
        return self.value,
    def __repr__(self):
        return "Return(%s)" % (repr(self.value),)

class Add(Node):
    nodes["add"] = "Add"
    def __init__(self, (left, right)):
        self.left = left
        self.right = right
    def _getChildren(self):
        return self.left, self.right
    def __repr__(self):
        return "Add(%s, %s)" % (repr(self.left), repr(self.right))

class Function(Node):
    nodes["function"] = "Function"
    def __init__(self, name, argnames, defaults, flags, doc, code):
        self.name = name
        self.argnames = argnames
        self.defaults = defaults
        self.flags = flags
        self.doc = doc
        self.code = code
        self.varargs = self.kwargs = None
        if flags & CO_VARARGS:
            self.varargs = 1
        if flags & CO_VARKEYWORDS:
            self.kwargs = 1


    def _getChildren(self):
        return self.name, self.argnames, self.defaults, self.flags, self.doc, self.code
    def __repr__(self):
        return "Function(%s, %s, %s, %s, %s, %s)" % (repr(self.name), repr(self.argnames), repr(self.defaults), repr(self.flags), repr(self.doc), repr(self.code))

class TryExcept(Node):
    nodes["tryexcept"] = "TryExcept"
    def __init__(self, body, handlers, else_):
        self.body = body
        self.handlers = handlers
        self.else_ = else_
    def _getChildren(self):
        return self.body, self.handlers, self.else_
    def __repr__(self):
        return "TryExcept(%s, %s, %s)" % (repr(self.body), repr(self.handlers), repr(self.else_))

class Subscript(Node):
    nodes["subscript"] = "Subscript"
    def __init__(self, expr, flags, subs):
        self.expr = expr
        self.flags = flags
        self.subs = subs
    def _getChildren(self):
        return self.expr, self.flags, self.subs
    def __repr__(self):
        return "Subscript(%s, %s, %s)" % (repr(self.expr), repr(self.flags), repr(self.subs))

class Ellipsis(Node):
    nodes["ellipsis"] = "Ellipsis"
    def __init__(self, ):
        pass
    def _getChildren(self):
        return ()
    def __repr__(self):
        return "Ellipsis()"

class Print(Node):
    nodes["print"] = "Print"
    def __init__(self, nodes, dest):
        self.nodes = nodes
        self.dest = dest
    def _getChildren(self):
        return self.nodes, self.dest
    def __repr__(self):
        return "Print(%s, %s)" % (repr(self.nodes), repr(self.dest))

class UnaryAdd(Node):
    nodes["unaryadd"] = "UnaryAdd"
    def __init__(self, expr):
        self.expr = expr
    def _getChildren(self):
        return self.expr,
    def __repr__(self):
        return "UnaryAdd(%s)" % (repr(self.expr),)

class ListCompFor(Node):
    nodes["listcompfor"] = "ListCompFor"
    def __init__(self, assign, list, ifs):
        self.assign = assign
        self.list = list
        self.ifs = ifs
    def _getChildren(self):
        return self.assign, self.list, self.ifs
    def __repr__(self):
        return "ListCompFor(%s, %s, %s)" % (repr(self.assign), repr(self.list), repr(self.ifs))

class Dict(Node):
    nodes["dict"] = "Dict"
    def __init__(self, items):
        self.items = items
    def _getChildren(self):
        return self.items,
    def __repr__(self):
        return "Dict(%s)" % (repr(self.items),)

class Getattr(Node):
    nodes["getattr"] = "Getattr"
    def __init__(self, expr, attrname):
        self.expr = expr
        self.attrname = attrname
    def _getChildren(self):
        return self.expr, self.attrname
    def __repr__(self):
        return "Getattr(%s, %s)" % (repr(self.expr), repr(self.attrname))

class AssList(Node):
    nodes["asslist"] = "AssList"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "AssList(%s)" % (repr(self.nodes),)

class UnarySub(Node):
    nodes["unarysub"] = "UnarySub"
    def __init__(self, expr):
        self.expr = expr
    def _getChildren(self):
        return self.expr,
    def __repr__(self):
        return "UnarySub(%s)" % (repr(self.expr),)

class Sliceobj(Node):
    nodes["sliceobj"] = "Sliceobj"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "Sliceobj(%s)" % (repr(self.nodes),)

class Invert(Node):
    nodes["invert"] = "Invert"
    def __init__(self, expr):
        self.expr = expr
    def _getChildren(self):
        return self.expr,
    def __repr__(self):
        return "Invert(%s)" % (repr(self.expr),)

class Name(Node):
    nodes["name"] = "Name"
    def __init__(self, name):
        self.name = name
    def _getChildren(self):
        return self.name,
    def __repr__(self):
        return "Name(%s)" % (repr(self.name),)

class AssTuple(Node):
    nodes["asstuple"] = "AssTuple"
    def __init__(self, nodes):
        self.nodes = nodes
    def _getChildren(self):
        return self.nodes,
    def __repr__(self):
        return "AssTuple(%s)" % (repr(self.nodes),)

class For(Node):
    nodes["for"] = "For"
    def __init__(self, assign, list, body, else_):
        self.assign = assign
        self.list = list
        self.body = body
        self.else_ = else_
    def _getChildren(self):
        return self.assign, self.list, self.body, self.else_
    def __repr__(self):
        return "For(%s, %s, %s, %s)" % (repr(self.assign), repr(self.list), repr(self.body), repr(self.else_))

class Raise(Node):
    nodes["raise"] = "Raise"
    def __init__(self, expr1, expr2, expr3):
        self.expr1 = expr1
        self.expr2 = expr2
        self.expr3 = expr3
    def _getChildren(self):
        return self.expr1, self.expr2, self.expr3
    def __repr__(self):
        return "Raise(%s, %s, %s)" % (repr(self.expr1), repr(self.expr2), repr(self.expr3))

class From(Node):
    nodes["from"] = "From"
    def __init__(self, modname, names):
        self.modname = modname
        self.names = names
    def _getChildren(self):
        return self.modname, self.names
    def __repr__(self):
        return "From(%s, %s)" % (repr(self.modname), repr(self.names))

class Slice(Node):
    nodes["slice"] = "Slice"
    def __init__(self, expr, flags, lower, upper):
        self.expr = expr
        self.flags = flags
        self.lower = lower
        self.upper = upper
    def _getChildren(self):
        return self.expr, self.flags, self.lower, self.upper
    def __repr__(self):
        return "Slice(%s, %s, %s, %s)" % (repr(self.expr), repr(self.flags), repr(self.lower), repr(self.upper))

klasses = globals()
for k in nodes.keys():
    nodes[k] = klasses[nodes[k]]
