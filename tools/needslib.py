"""Every construct a corpus file needs beyond the trunk compiler, by family.

The core census (censuslib) names a file's first construct outside the
compiler's scope and stops. This walk records every such construct instead, so
a census can ask which files a set of feature families would bring into scope:
lists alone, `Map` alone, error values alone, and any union of them, and which
of those files also need strings.

It reads `--emit=ast` text, as censuslib does, and applies the same scope rules
(docs/TYPED.md's core plus the enum and `match` extension). A receiver's
family (`xs.len`, `xs[i]`, `for x in xs`) is read from a small local type
environment: annotations, list and map constructors, literals, struct fields
and function results. A receiver whose type it cannot read is labelled by the
method's name alone (`unknown:` when even that is ambiguous). This is a scope
prediction, never a type checker and never a claim that a program runs.

Spec: type.list.lit, type.map, type.row, mem.list.pop, mem.map.absent,
type.method.resolve, mem.iter.for, mem.iter.range.
"""
import itertools

import censuslib
from censuslib import CORE_TYPES, CORE_FUNCTIONS, BINARY, ASSIGN, ITEM_OUT

# Builtin methods (type.method.resolve step 1) and the list and map properties.
LIST_METHODS = {'push', 'pop', 'get', 'first', 'last', 'is_empty', 'count', 'len', 'clear', 'reserve', 'reset'}
MAP_METHODS = {'pairs', 'is_empty', 'clear', 'remove', 'count', 'len'}
# std.list and std.map home-module candidates take fn values or generics.
LIST_HOME = {'map', 'filter', 'fold', 'sum', 'sort_by', 'sorted_by', 'sorted', 'enumerate', 'zip',
             'collect', 'par', 'any', 'all', 'count_where', 'index_where', 'find_where', 'min_by',
             'max_by', 'contains', 'index_of', 'reverse', 'reversed', 'join', 'concat', 'extend'}
MAP_HOME = {'has', 'get', 'get_or', 'tally', 'keys', 'values'}
# What the `str` methods that build lists or views answer.
STR_RESULTS = {'bytes': ('List', ('byte',)), 'chars': ('List', ('char',)), 'lines': ('List', ('str',)),
               'words': ('List', ('str',)), 'split': ('List', ('str',)), 'trim': ('str',),
               'to_upper': ('str',), 'to_lower': ('str',), 'repeat': ('str',), 'replace': ('str',)}
FAMILIES = ('list', 'map', 'err', 'str', 'range', 'tuple', 'mode', 'cast', 'unknown', 'other')


def family(label):
    return label.split(':', 1)[0]


class Needs:
    """Walk every node of one file; `run()` answers {label: [line, col]}."""

    def __init__(self, tree, prelude):
        t = self.t = tree
        self.prelude = prelude
        self.labels = {}
        self.fns, self.structs, self.enums, self.variants, self.aliases = {}, {}, {}, set(), set()
        for item in t.children(t.root):
            for d in t.children(item):
                k = t.kind(d)
                children = t.children(d)
                if k == 'Function':
                    name = t.spell(next(c for c in children if t.kind(c) == 'Name'))
                    result = next((t.children(c)[0] for c in children if t.kind(c) == 'ReturnType'), -1)
                    self.fns[name] = self.of_type(result) if result >= 0 else ('unit',)
                elif k == 'Struct':
                    fields = {}
                    for c in children:
                        if t.kind(c) == 'Fields':
                            for f in t.children(c):
                                fname = next(g for g in t.children(f) if t.kind(g) == 'Name')
                                ftype = [g for g in t.children(f) if t.kind(g) not in ('Name', 'Visibility', 'Attribute')]
                                fields[t.spell(fname)] = ftype[0] if ftype else -1
                    self.structs[t.spell(children[0])] = fields
                elif k in ('Enum', 'TypeAlias') and any(t.kind(c) == 'Variants' for c in children):
                    name = next(c for c in children if t.kind(c) == 'Name')
                    self.enums[t.spell(name)] = d
                    for c in children:
                        if t.kind(c) == 'Variants':
                            for v in t.children(c):
                                self.variants.add(t.spell(t.children(v)[0]))
                elif k == 'ErrorAlias':
                    self.aliases.add(t.spell(children[0]))
        self.fields = {f for fields in self.structs.values() for f in fields}
        self.scopes = []
        self.loops = 0
        self.fallible = False

    # -- recording -----------------------------------------------------------
    def need(self, label, node):
        if label not in self.labels:
            self.labels[label] = self.t.where(node)

    def run(self):
        t = self.t
        for c in t.children(t.root):
            if t.kind(c) == 'InnerAttribute':
                self.need('other:attribute', c)
            for d in t.children(c):
                self.item(d)
        return self.labels

    # -- types ---------------------------------------------------------------
    def of_type(self, n):
        """A small descriptor of a written type: ('List', e), ('Map', k, v),
        ('err', t), ('str',), ('int',), ('struct', name), or ('?',)."""
        t = self.t
        if n < 0:
            return ('?',)
        k = t.kind(n)
        if k == 'NamedType':
            cs = t.children(n)
            names = t.children(cs[0])
            name = t.spell(names[-1])
            if len(cs) > 1:
                args = t.children(cs[1])
                if name == 'List' and args:
                    return ('List', self.of_name(args[0]))
                if name == 'Map' and len(args) == 2:
                    return ('Map', self.of_name(args[0]), self.of_name(args[1]))
                return ('generic', name)
            if name in self.structs:
                return ('struct', name)
            if name in self.enums:
                return ('enum', name)
            return (name,)
        if k == 'ErrorType':
            return ('err', self.of_type(t.children(n)[0]))
        if k == 'PrefixType' and t.spell(n) == '!':
            return ('err', self.of_type(t.children(n)[0]))
        if k == 'TupleType':
            return ('Tuple',) + tuple(self.of_type(c) for c in t.children(n)) if t.children(n) else ('unit',)
        return ('?',)

    def type(self, n):
        t = self.t
        k = t.kind(n)
        if k == 'NamedType':
            cs = t.children(n)
            names = t.children(cs[0])
            name = t.spell(names[-1])
            if len(names) != 1:
                self.need('other:qualified type', n)
                return
            if len(cs) > 1:
                args = t.children(cs[1])
                if name in ('List', 'Map'):
                    self.need(name.lower() + ':type', n)
                    for a in args:
                        self.type_argument(a)
                else:
                    self.need('other:generic type `%s`' % name, n)
                return
            if name in self.structs or name in self.enums or name in self.fns:
                return
            if name in self.prelude and name not in CORE_TYPES:
                self.need(('str:type `%s`' if name in ('char', 'byte') else 'other:type `%s`') % name, n)
            return
        if k == 'TupleType':
            if t.children(n):
                self.need('tuple:type', n)
                for c in t.children(n):
                    self.type(c)
            return
        if k == 'ErrorType':
            self.need('err:row type', n)
            inner, row = t.children(n)[0], t.children(n)[1:]
            self.type(inner)
            for r in row:
                if t.kind(r) == 'ErrorRow':
                    for entry in t.children(r):
                        for payload in t.children(entry)[1:]:
                            self.type(payload)
            return
        if k == 'PrefixType' and t.spell(n) == '!':
            self.need('err:`!T` type', n)
            self.type(t.children(n)[0])
            return
        if k in ('PrefixType', 'BuiltinType'):
            self.need('other:`%s` type' % t.spell(n), n)
            return
        self.need({'FunctionType': 'other:fn type'}.get(k, 'other:type `%s`' % k), n)

    # -- items ---------------------------------------------------------------
    def item(self, d):
        t = self.t
        k = t.kind(d)
        if k == 'Attribute':
            self.need('other:attribute', d)
            return
        if k == 'Visibility':
            return
        if d in self.enums.values():
            for c in t.children(d):
                if t.kind(c) == 'Generics':
                    self.need('other:generics', c)
                if t.kind(c) == 'Variants':
                    for variant in t.children(c):
                        for payload in t.children(variant)[1:]:
                            self.type(payload)
            return
        if k == 'ErrorAlias':
            self.need('err:error alias', d)
            return
        if k in ITEM_OUT:
            self.need('other:' + ITEM_OUT[k], d)
            return
        if k == 'Function':
            self.function(d)
        elif k == 'Struct':
            for c in t.children(d):
                if t.kind(c) == 'Generics':
                    self.need('other:generics', c)
                if t.kind(c) == 'Fields':
                    for f in t.children(c):
                        for g in t.children(f):
                            if t.kind(g) == 'Attribute':
                                self.need('other:attribute', g)
                            elif t.kind(g) not in ('Visibility', 'Name'):
                                self.type(g)
        else:
            self.need('other:item `%s`' % k, d)

    def function(self, n):
        t = self.t
        body = None
        params = {}
        self.fallible = False
        for c in t.children(n):
            k = t.kind(c)
            if k == 'Qualifier':
                self.need('other:`%s` fn' % t.spell(c), c)
            elif k == 'Generics':
                self.need('other:generics', c)
            elif k == 'Parameters':
                for p in t.children(c):
                    if t.kind(p) == 'Variadic':
                        self.need('other:variadic', p)
                        continue
                    name, ty = None, ('?',)
                    for q in t.children(p):
                        kq = t.kind(q)
                        if kq == 'Mode':
                            self.need('mode:parameter `%s`' % t.spell(q), q)
                        elif kq == 'ViewSet':
                            self.need('other:view set', q)
                        elif kq == 'Name':
                            if t.spell(q) == 'self':
                                self.need('other:`self` receiver', q)
                            name = t.spell(q)
                        else:
                            self.type(q)
                            ty = self.of_type(q)
                    if name:
                        params[name] = ty
            elif k == 'ReturnType':
                ty = t.children(c)[0]
                if t.kind(ty) == 'PrefixType' and t.spell(ty) == '!':
                    self.fallible = True
                    self.type(t.children(ty)[0])
                elif t.kind(ty) == 'ErrorType':
                    self.fallible = True
                    self.type(ty)
                else:
                    self.type(ty)
            elif k == 'Block':
                body = c
        if body is None:
            self.need('other:bodyless fn', n)
            return
        self.scopes = [params]
        self.block(body)
        self.scopes = []

    # -- scopes --------------------------------------------------------------
    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def bind(self, name, ty):
        self.scopes[-1][name] = ty

    # -- statements ----------------------------------------------------------
    def block(self, n):
        t = self.t
        self.scopes.append({})
        for st in t.children(n):
            for d in t.children(st):
                k = t.kind(d)
                if k == 'Attribute':
                    self.need('other:attribute', d)
                elif t.kind(st) == 'Tail':
                    self.expr(d)
                elif k == 'Item':
                    for x in t.children(d):
                        if t.kind(x) == 'Visibility':
                            continue
                        if t.kind(x) == 'Attribute':
                            self.need('other:attribute', x)
                        elif t.kind(x) != 'Bindings':
                            self.need('other:nested item', x)
                        else:
                            self.bindings(x)
                elif k == 'Assignment':
                    self.assignment(d)
                elif k == 'Defer':
                    self.need('other:`%s`' % t.spell(d), d)
                    for c in t.children(d):
                        if t.kind(c) != 'DeferKind':
                            self.expr(c)
                elif k == 'Assume':
                    self.need('other:`assume`', d)
                else:
                    self.expr(d)
        self.scopes.pop()

    def bindings(self, n):
        t = self.t
        cs = t.children(n)
        if t.spell(cs[0]) == 'const':
            self.need('other:`const`', cs[0])
        for b in cs[1:]:
            parts = t.children(b)
            pat = parts[0]
            annotated = None
            for q in parts[1:-1]:
                self.type(q)
                annotated = self.of_type(q)
            value = self.expr(parts[-1])
            ty = annotated or value
            self.bind_pattern(pat, ty, let=True)

    def bind_pattern(self, pat, ty, let=False):
        t = self.t
        kp = t.kind(pat)
        if kp == 'NamePattern':
            names = t.children(t.children(pat)[0])
            if len(names) != 1:
                self.need('other:qualified pattern', pat)
                return
            self.bind(t.spell(names[0]), ty)
        elif kp == 'TuplePattern':
            self.need('tuple:pattern', pat)
            parts = ty[1:] if ty and ty[0] == 'Tuple' else ()
            for i, c in enumerate(t.children(pat)):
                self.bind_pattern(c, parts[i] if i < len(parts) else ('?',), let)
        elif kp == 'WildcardPattern':
            return
        elif let:
            self.need('other:pattern `%s`' % kp, pat)

    def assignment(self, n):
        t = self.t
        cs = t.children(n)
        place = cs[0]
        if t.kind(place) == 'Index':
            receiver = t.children(place)[0]
            rt = self.expr(receiver)
            fam = self.container(rt, 'index')
            self.need(fam + ':index store', place)
            for a in t.children(t.children(place)[1]):
                self.argument(a)
            if fam == 'map' and t.spell(cs[1]) != '=':
                self.need('map:compound index store', cs[1])
        else:
            self.expr(place)
            if t.kind(place) not in ('Name', 'Member'):
                self.need('other:assignment place', place)
        if t.spell(cs[1]) not in ASSIGN:
            self.need('other:assignment `%s`' % t.spell(cs[1]), cs[1])
        for c in cs[2:]:
            if t.kind(c) == 'Mode':
                self.need('mode:store `%s`' % t.spell(c), c)
            else:
                self.expr(c)

    # -- expressions ---------------------------------------------------------
    def container(self, ty, what):
        if ty and ty[0] == 'List':
            return 'list'
        if ty and ty[0] == 'Map':
            return 'map'
        if ty and ty[0] in ('str',):
            return 'str'
        return 'unknown'

    def argument(self, a):
        t = self.t
        cs = t.children(a)
        if cs and t.kind(cs[0]) == 'Mode':
            self.need('mode:argument `%s`' % t.spell(cs[0]), cs[0])
            return self.expr(cs[1]) if len(cs) > 1 else ('?',)
        return self.expr(cs[0]) if cs else ('?',)

    def name(self, n, call):
        t = self.t
        name = t.spell(n)
        local = self.lookup(name)
        if local is not None:
            return local
        if name in self.fns:
            if not call:
                self.need('other:a function used as a value', n)
            return self.fns[name]
        if name in self.structs:
            self.need('other:a type used as a value', n)
            return ('?',)
        if name in self.prelude:
            if name in CORE_TYPES:
                self.need('other:a type used as a value', n)
            elif name not in CORE_FUNCTIONS:
                fam = 'str' if name in ('str_from_utf8',) else 'other'
                self.need('%s:prelude `%s`' % (fam, name), n)
            return ('?',)
        self.need('err:error tag' if self.fallible else 'unknown:unresolved name', n)
        return ('?',)

    def str_result(self, method):
        return STR_RESULTS.get(method, ('?',))

    def expr(self, n):
        """Walk `n`, record its needs, and answer its type descriptor."""
        t = self.t
        k = t.kind(n)
        cs = t.children(n)
        if k == 'Name':
            return self.name(n, False)
        if k == 'Literal':
            tok = t.tok(n)
            if tok in ('int', 'true', 'false'):
                return ('bool',) if tok != 'int' else ('int',)
            if tok == 'raw':
                return ('str',)
            self.need(('str:%s literal' if tok == 'char' else 'other:%s literal') % tok, n)
            return ('?',)
        if k == 'String':
            multi = t.tok(n) == 'multi-open'
            for c in cs:
                if t.kind(c) == 'Interpolation':
                    if multi:
                        self.need('other:interpolation in a multiline string', c)
                    parts = t.children(c)
                    if len(parts) > 1:
                        self.need('str:format spec', parts[1])
                    hole = self.expr(parts[0])
                    if hole and hole[0] in ('List', 'Map', 'Tuple', 'err', 'enum'):
                        self.need({'List': 'list', 'Map': 'map', 'Tuple': 'tuple', 'err': 'err',
                                   'enum': 'str'}[hole[0]] + ':rendered in a string', c)
            return ('str',)
        if k == 'Group':
            return self.expr(cs[0])
        if k == 'Prefix':
            op = t.spell(cs[0])
            if op not in ('-', '!') or t.kind(cs[1]) == 'Mode':
                self.need('other:prefix `%s`' % op, n)
            return self.expr(cs[-1])
        if k == 'Binary':
            a, op, b = cs
            left = self.expr(a)
            if t.spell(op) not in BINARY:
                self.need('other:operator `%s`' % t.spell(op), op)
            right = self.expr(b)
            if t.spell(op) in ('==', '!=', '<', '<=', '>', '>=', '&&', '||'):
                return ('bool',)
            return left if left != ('?',) else right
        if k == 'Call':
            return self.call(n)
        if k == 'StructLiteral':
            if t.kind(cs[0]) != 'Name':
                self.need('other:qualified struct literal', cs[0])
            for f in cs[1:]:
                parts = t.children(f)
                if len(parts) > 1:
                    self.expr(parts[1])
                else:
                    self.name(parts[0], False)
            return ('struct', t.spell(cs[0]))
        if k == 'Member':
            recv, member = cs
            if t.kind(recv) == 'Name' and t.spell(recv) in self.enums and not self.lookup(t.spell(recv)):
                return ('enum', t.spell(recv))
            if t.kind(recv) == 'Receiver':
                self.need('other:moded receiver', recv)
            rt = self.expr(recv)
            if t.tok(member) == 'int':
                self.need('tuple:index', member)
                index = int(t.spell(member))
                return rt[1 + index] if rt and rt[0] == 'Tuple' and index + 1 < len(rt) else ('?',)
            field = t.spell(member)
            if rt and rt[0] == 'struct' and field in self.structs.get(rt[1], {}):
                return self.of_type(self.structs[rt[1]][field])
            if field == 'len':
                fam = self.container(rt, 'len')
                if fam == 'unknown' and field in self.fields:
                    return ('?',)
                self.need(fam + ':`len`', member)
                return ('int',)
            if rt and rt[0] == 'err':
                self.need('err:member of a row', member)
            if field not in self.fields:
                self.need('other:member `%s`' % field, member)
            return ('?',)
        if k == 'If':
            out = ('?',)
            for c in cs:
                if t.kind(c) == 'Block':
                    self.block(c)
                else:
                    ty = self.expr(c)
                    out = out if out != ('?',) else ty
            return ('?',)
        if k == 'Block':
            self.block(n)
            return ('?',)
        if k == 'Loop':
            word = t.spell(cs[0])
            if word == 'while':
                self.expr(cs[1])
                self.loops += 1
                self.block(cs[2])
                self.loops -= 1
                return ('unit',)
            if word == 'loop':
                self.need('other:`loop` loop', n)
                self.loops += 1
                self.block(cs[-1])
                self.loops -= 1
                return ('?',)
            pat, header, body = cs[1], cs[2], cs[3]
            elem = ('?',)
            if t.kind(header) == 'Range':
                self.need('range:`for` over a range', header)
                for c in t.children(header):
                    if t.kind(c) != 'Operator':
                        self.expr(c)
                elem = ('int',)
            else:
                ht = self.expr(header)
                fam = self.container(ht, 'for')
                self.need(fam + ':`for` iteration', n)
                if ht and ht[0] == 'List':
                    elem = ht[1]
            self.scopes.append({})
            self.bind_pattern(pat, elem)
            if t.kind(pat) not in ('NamePattern', 'WildcardPattern', 'TuplePattern'):
                self.need('other:`for` pattern `%s`' % t.kind(pat), pat)
            self.loops += 1
            self.block(body)
            self.loops -= 1
            self.scopes.pop()
            return ('unit',)
        if k == 'Jump':
            word = t.spell(cs[0])
            if word != 'return':
                if len(cs) > 1:
                    self.need('other:`%s` value' % word, n)
                return ('never',)
            if len(cs) > 1:
                self.expr(cs[1])
            return ('never',)
        if k == 'Match':
            st = self.expr(cs[0])
            if st and st[0] == 'err':
                self.need('err:`match` over a row', n)
            for arm in cs[1:]:
                parts = t.children(arm)
                self.scopes.append({})
                self.pattern(parts[0], st)
                for part in parts[1:]:
                    self.expr(t.children(part)[0] if t.kind(part) == 'Guard' else part)
                self.scopes.pop()
            return ('?',)
        if k == 'List':
            if not cs:
                self.need('other:an empty list literal', n)
            self.need('list:literal', n)
            first = ('?',)
            for c in cs:
                ty = self.expr(c)
                first = first if first != ('?',) else ty
            return ('List', first)
        if k == 'Index':
            recv, args = cs
            rt = self.expr(recv)
            fam = self.container(rt, 'index')
            slicing = False
            for a in t.children(args):
                inner = t.children(a)
                if inner and t.kind(inner[-1]) in ('Range', 'FromEnd'):
                    slicing = True
                    for c in t.children(inner[-1]):
                        if t.kind(c) != 'Operator':
                            self.expr(c)
                else:
                    self.argument(a)
            self.need(fam + (':slice' if slicing else ':index'), n)
            if fam == 'list':
                return rt if slicing else rt[1]
            if fam == 'map':
                return ('err', rt[2])
            if fam == 'str':
                return ('str',)
            return ('?',)
        if k == 'Propagate':
            self.need('err:`?` propagation', n)
            inner = self.expr(cs[0])
            return inner[1] if inner and inner[0] == 'err' else ('?',)
        if k == 'Default':
            self.need('err:`else` default', n)
            left = self.expr(cs[0])
            fallback = cs[-1]
            if t.kind(fallback) == 'Handler':
                self.need('err:`else` handler', fallback)
                hp = t.children(fallback)
                self.scopes.append({})
                self.pattern(hp[0], ('?',))
                for c in hp[1:]:
                    self.expr(c)
                self.scopes.pop()
            else:
                self.expr(fallback)
            return left[1] if left and left[0] == 'err' else left
        if k == 'Tuple':
            self.need('tuple:value', n)
            return ('Tuple',) + tuple(self.expr(c) for c in cs)
        if k == 'Range':
            self.need('range:value', n)
            for c in cs:
                if t.kind(c) != 'Operator':
                    self.expr(c)
            return ('range',)
        if k == 'Cast':
            self.need('cast:`as`', n)
            self.expr(cs[0])
            return (t.spell(cs[-1]),) if cs else ('?',)
        if k == 'Receiver':
            mode, inner = cs[0], cs[-1]
            return self.expr(inner)
        name = censuslib.EXPR_OUT.get(k, 'expression `%s`' % k)
        self.need('other:' + name, n)
        for c in cs:
            if t.kind(c) not in ('Operator', 'Mode', 'Path', 'Name'):
                self.expr(c)
        return ('?',)

    def call(self, n):
        t = self.t
        recv, args = t.children(n)
        kr = t.kind(recv)
        if kr == 'Member':
            base, member = t.children(recv)
            moded = t.kind(base) == 'Receiver'
            method = t.spell(member)
            if t.kind(base) == 'Name' and t.spell(base) in self.enums and not self.lookup(t.spell(base)):
                for a in t.children(args):
                    self.argument(a)
                return ('enum', t.spell(base))
            rt = self.expr(base)
            fam = self.container(rt, 'method')
            if fam == 'unknown':
                if method in LIST_METHODS - MAP_METHODS - {'get'}:
                    fam = 'list'
                elif method in ('pairs',):
                    fam = 'map'
                elif method in LIST_HOME or method in MAP_HOME:
                    fam = 'other'
            if fam == 'list':
                label = 'list:method `%s`' % method if method in LIST_METHODS else 'other:std.list `%s`' % method
            elif fam == 'map':
                label = 'map:method `%s`' % method if method in MAP_METHODS else 'other:std.map `%s`' % method
            elif fam == 'str':
                label = 'str:method `%s`' % method
            elif fam == 'other':
                label = 'other:method `%s`' % method
            else:
                label = 'unknown:method `%s`' % method
            self.need(label, n)
            if moded and fam not in ('list', 'map'):
                self.need('other:moded receiver', base)
            for a in t.children(args):
                self.argument(a)
            if fam == 'list' and rt and rt[0] == 'List':
                if method in ('pop', 'get', 'first', 'last'):
                    return ('err', rt[1])
                if method in ('count',):
                    return ('int',)
                if method in ('is_empty',):
                    return ('bool',)
                return ('unit',)
            if fam == 'map' and rt and rt[0] == 'Map':
                if method == 'pairs':
                    return ('List', ('Tuple', rt[1], rt[2]))
                if method == 'remove':
                    return ('err', rt[2])
                if method == 'count':
                    return ('int',)
                if method == 'is_empty':
                    return ('bool',)
            if fam == 'str':
                return self.str_result(method)
            return ('?',)
        if kr == 'Index':
            head, iargs = t.children(recv)
            name = t.spell(head) if t.kind(head) == 'Name' else None
            if name in ('List', 'Map') and not self.lookup(name):
                self.need(name.lower() + ':constructor', n)
                types = [t.children(a)[-1] for a in t.children(iargs)]
                for ty in types:
                    self.type_argument(ty)
                for a in t.children(args):
                    self.argument(a)
                if name == 'List' and len(types) == 1:
                    return ('List', self.of_name(types[0]))
                if name == 'Map' and len(types) == 2:
                    return ('Map', self.of_name(types[0]), self.of_name(types[1]))
                return ('?',)
            self.need('other:generic application', n)
            for a in t.children(args):
                self.argument(a)
            return ('?',)
        if kr != 'Name':
            self.need('other:call of a computed value', n)
            self.expr(recv)
            for a in t.children(args):
                self.argument(a)
            return ('?',)
        name = t.spell(recv)
        local = self.lookup(name)
        result = ('?',)
        if local is None and name in self.fns:
            result = self.fns[name]
            if result and result[0] == 'err':
                self.need('err:a call of a fallible function', n)
        elif local is None and name in self.prelude:
            if name in CORE_TYPES:
                self.need('other:a type used as a value', recv)
            elif name not in CORE_FUNCTIONS:
                fam = 'str' if name in ('str_from_utf8',) else 'other'
                self.need('%s:prelude `%s`' % (fam, name), recv)
        elif local is None and name in self.structs:
            self.need('other:a type used as a value', recv)
        elif local is None:
            self.need('err:error tag' if self.fallible else 'other:unresolved call `%s`' % name, recv)
        else:
            self.need('other:call of a computed value', n)
        for a in t.children(args):
            self.argument(a)
        return result

    def type_argument(self, n):
        if self.t.kind(n) in ('NamedType', 'TupleType', 'ErrorType', 'PrefixType', 'FunctionType'):
            self.type(n)
        else:
            self.typename(n)

    def typename(self, n):
        """An index argument naming a type spelled as an expression (`List[int]()`)."""
        t = self.t
        if t.kind(n) == 'Name':
            name = t.spell(n)
            if name in self.structs or name in self.enums or name in CORE_TYPES:
                return
            if name in self.prelude:
                self.need(('str:type `%s`' if name in ('char', 'byte') else 'other:type `%s`') % name, n)
                return
            self.need('other:type `%s`' % name, n)
            return
        if t.kind(n) == 'Index':
            head, iargs = t.children(n)
            name = t.spell(head) if t.kind(head) == 'Name' else '?'
            if name in ('List', 'Map'):
                self.need(name.lower() + ':type', n)
                for a in t.children(iargs):
                    self.typename(t.children(a)[-1])
                return
            self.need('other:generic type `%s`' % name, n)
            return
        if t.kind(n) == 'Tuple':
            self.need('tuple:type', n)
            for c in t.children(n):
                self.type_argument(c)
            return
        self.need('other:type expression `%s`' % t.kind(n), n)

    def of_name(self, n):
        t = self.t
        if t.kind(n) == 'Name':
            name = t.spell(n)
            if name in self.structs:
                return ('struct', name)
            if name in self.enums:
                return ('enum', name)
            return (name,)
        if t.kind(n) == 'Index':
            head, iargs = t.children(n)
            args = [t.children(a)[-1] for a in t.children(iargs)]
            if t.spell(head) == 'List' and len(args) == 1:
                return ('List', self.of_name(args[0]))
            if t.spell(head) == 'Map' and len(args) == 2:
                return ('Map', self.of_name(args[0]), self.of_name(args[1]))
        if t.kind(n) in ('NamedType', 'TupleType', 'ErrorType', 'PrefixType'):
            return self.of_type(n)
        return ('?',)

    # -- patterns ------------------------------------------------------------
    def pattern(self, n, ty):
        t = self.t
        k, cs = t.kind(n), t.children(n)
        if k == 'WildcardPattern':
            return
        if k == 'NamePattern':
            names = t.children(cs[0])
            spelled = t.spell(names[0])
            if len(names) == 1 and spelled not in self.variants:
                if ty and ty[0] == 'err' and not self.fallible:
                    pass
                self.bind(spelled, ty if spelled[:1].islower() or True else ('?',))
            return
        if k == 'LiteralPattern':
            self.expr(cs[0])
            return
        if k == 'RangePattern':
            self.expr(cs[0]); self.expr(cs[2])
            return
        if k == 'AtPattern':
            self.bind(t.spell(t.children(cs[0])[0]), ty)
            self.pattern(cs[1], ty)
            return
        if k == 'StructPattern':
            for field in cs[1:]:
                if t.kind(field) == 'RestPattern':
                    continue
                parts = t.children(field)
                if len(parts) > 1:
                    self.pattern(parts[1], ('?',))
                else:
                    self.bind(t.spell(parts[0]), ('?',))
            return
        if k == 'ConstructorPattern':
            head = t.children(cs[0])
            if t.spell(head[-1]) not in self.variants:
                self.need('err:tag pattern', n)
            for part in cs[1:]:
                self.pattern(part, ('?',))
            return
        if k == 'OrPattern':
            for part in cs:
                self.pattern(part, ty)
            return
        if k == 'TuplePattern':
            self.need('tuple:pattern', n)
            for c in cs:
                self.pattern(c, ('?',))
            return
        self.need('other:pattern `%s`' % k, n)


class CurrentNeeds(Needs):
    """Missing constructs after collections, not the historical fn05 inventory.

    Keep unknown types explicit. Successful baseline rows are established by
    execution, independently of this intentionally incomplete local type model.
    """
    LIST_IMPLEMENTED = {'push', 'pop', 'get', 'first', 'last', 'is_empty', 'count', 'len', 'clear'}
    MAP_IMPLEMENTED = {'pairs', 'is_empty', 'clear', 'remove', 'count', 'len'}

    def __init__(self, tree, prelude):
        super().__init__(tree, prelude)
        self.value_types = {}
        self.variant_payloads = {}
        for name, node in self.enums.items():
            variants = {}
            for part in tree.children(node):
                if tree.kind(part) == 'Variants':
                    for variant in tree.children(part):
                        fields = tree.children(variant)
                        variants[tree.spell(fields[0])] = tuple(self.of_type(p) for p in fields[1:])
            self.variant_payloads[name] = variants
        self.tag_payloads = {}
        work = [tree.root]
        while work:
            node = work.pop()
            parts = tree.children(node)
            if tree.kind(node) == 'RowEntry' and parts:
                names = tree.children(parts[0])
                name = tree.spell(names[-1])
                if name not in self.aliases:
                    payload = tuple(self.of_type(p) for p in parts[1:])
                    if name in self.tag_payloads and self.tag_payloads[name] != payload:
                        self.tag_payloads[name] = None
                    else:
                        self.tag_payloads[name] = payload
            work.extend(reversed(parts))

    def str_result(self, method):
        fixed = {'to_int': ('err', ('int',)), 'find': ('err', ('int',)), 'get': ('err', ('str',)),
                 'count': ('int',), 'len': ('int',), 'is_empty': ('bool',), 'contains': ('bool',),
                 'starts_with': ('bool',), 'ends_with': ('bool',), 'trim_start': ('str',), 'trim_end': ('str',)}
        return fixed.get(method, super().str_result(method))

    @staticmethod
    def joined(types):
        live = [ty for ty in types if ty != ('never',)]
        return live[0] if live and all(ty == live[0] for ty in live) else ('?',)

    def block(self, node):
        super().block(node)
        statements = self.t.children(node)
        result = ('unit',)
        if statements:
            last = statements[-1]
            values = self.t.children(last)
            if values and self.t.kind(last) == 'Tail':
                result = self.value_types.get(values[-1], ('?',))
            elif values and self.value_types.get(values[-1]) == ('never',):
                result = ('never',)
        self.value_types[node] = result
        return result

    def need(self, label, node):
        fam, detail = label.split(':', 1)
        if fam in ('list', 'map'):
            if detail == 'rendered in a string':
                if fam == 'map':
                    super().need('render:map', node)
                return
            if detail.startswith('method `'):
                name = detail.split('`')[1]
                implemented = self.LIST_IMPLEMENTED if fam == 'list' else self.MAP_IMPLEMENTED
                if name not in implemented:
                    super().need(label, node)
                return
            return
        if fam in ('err', 'tuple') or label == 'range:`for` over a range':
            return
        super().need(label, node)

    def item(self, node):
        super().item(node)
        if self.t.kind(node) == 'ErrorAlias':
            for part in self.t.children(node):
                if self.t.kind(part) == 'ErrorRow':
                    for entry in self.t.children(part):
                        for payload in self.t.children(entry)[1:]:
                            self.type(payload)

    def pattern(self, node, ty):
        t = self.t
        kind, parts = t.kind(node), t.children(node)
        if kind == 'TuplePattern':
            self.need('pattern:tuple', node)
            items = ty[1:] if ty and ty[0] == 'Tuple' else ()
            for i, part in enumerate(parts):
                self.pattern(part, items[i] if i < len(items) else ('?',))
            return
        if kind == 'NamePattern':
            names = t.children(parts[0])
            name = t.spell(names[-1])
            cases = self.variant_payloads.get(ty[1], {}) if ty and ty[0] == 'enum' else {}
            if name in cases or (ty and ty[0] == 'err' and name in self.tag_payloads):
                return
            self.bind(name, ty[1] if ty and ty[0] == 'err' else ty)
            return
        if kind == 'ConstructorPattern':
            names = t.children(parts[0])
            name = t.spell(names[-1])
            owner = t.spell(names[-2]) if len(names) > 1 else (ty[1] if ty and ty[0] == 'enum' else None)
            payload = self.variant_payloads.get(owner, {}).get(name)
            if payload is None:
                payload = self.tag_payloads.get(name)
            for i, part in enumerate(parts[1:]):
                self.pattern(part, payload[i] if payload is not None and i < len(payload) else ('?',))
            return
        if kind == 'StructPattern':
            fields = self.structs.get(ty[1], {}) if ty and ty[0] == 'struct' else {}
            for field in parts[1:]:
                if t.kind(field) == 'RestPattern':
                    continue
                sub = t.children(field)
                name = t.spell(sub[0])
                field_type = self.of_type(fields[name]) if name in fields else ('?',)
                if len(sub) > 1:
                    self.pattern(sub[1], field_type)
                else:
                    self.bind(name, field_type)
            return
        super().pattern(node, ty)

    def rendering(self, ty, node, seen=None):
        seen = set() if seen is None else seen
        if not ty or ty in seen:
            return
        seen.add(ty)
        if ty[0] in ('enum', 'Map'):
            self.need('render:' + ('enum' if ty[0] == 'enum' else 'map'), node)
        if ty[0] in ('List', 'Map', 'Tuple', 'err'):
            for inner in ty[1:]:
                self.rendering(inner, node, seen)
        elif ty[0] == 'struct':
            for field in self.structs.get(ty[1], {}).values():
                self.rendering(self.of_type(field), node, seen)
        elif ty[0] == '?':
            self.need('unknown:rendering', node)

    def expr(self, node):
        t = self.t
        kind, parts = t.kind(node), t.children(node)
        if kind == 'String':
            for part in parts:
                if t.kind(part) != 'Interpolation':
                    continue
                if t.tok(node) == 'multi-open':
                    self.need('str:interpolation in a multiline string', part)
                values = t.children(part)
                if len(values) > 1:
                    self.need('str:format spec', values[1])
                self.rendering(self.expr(values[0]), part)
            result = ('str',)
        elif kind == 'Literal' and t.tok(node) == 'char':
            self.need('str:char literal', node)
            result = ('char',)
        else:
            result = super().expr(node)
            if kind == 'Block':
                result = self.value_types.get(node, ('?',))
            elif kind == 'If':
                result = self.joined([self.value_types.get(part, ('?',)) for part in parts[1:]]) if len(parts) > 2 else ('unit',)
            elif kind == 'Match':
                result = self.joined([self.value_types.get(t.children(arm)[-1], ('?',)) for arm in parts[1:]])
            elif kind == 'Binary' and t.spell(parts[1]) == '+':
                left, right = self.value_types.get(parts[0]), self.value_types.get(parts[2])
                if left in (('char',), ('str',)) and right in (('char',), ('str',)) and ('str',) in (left, right):
                    result = ('str',)
            elif kind == 'Call' and t.kind(parts[0]) == 'Name':
                name = t.spell(parts[0])
                if self.lookup(name) is None and name not in self.fns:
                    if name in ('print', 'assert'):
                        result = ('unit',)
                    elif name == 'str_from_utf8':
                        result = ('err', ('str',))
        self.value_types[node] = result
        return result


def project(capture, census, oracle, verdicts, prelude):
    """Classify sealed parser observations against a measured current baseline.

    Execution proves the baseline; this small syntactic model only predicts
    gains. Retain its inventory even on measured rows, and never turn an
    unmodelled, unmeasured row into an optimistic zero-needs prediction.
    """
    def indexed(rows):
        out = {row['file']: row for row in rows}
        if len(out) != len(rows):
            raise ValueError('duplicate projection input row')
        return out
    captured, classified, recorded, measured = map(indexed, (capture, census, oracle, verdicts))
    expected = {name for name, row in recorded.items() if (row.get('expected') or '').startswith('run(')}
    if set(captured) != expected or not set(measured) <= expected:
        raise ValueError('incomplete or foreign projection inputs')
    member_dirs = {name.rsplit('/', 1)[0] for name, row in recorded.items() if row['member']}
    rows = []
    for name in sorted(expected):
        observation, scope, reference = captured[name], classified[name], recorded[name]
        if (observation['sha256'] != scope['sha256'] or observation['sha256'] != reference['sha256']
                or observation['ast_status'] != scope['ast']):
            raise ValueError('stale projection source or parser observation: ' + name)
        native = (reference.get('native_run') or reference['wolf'])['verdict']
        baseline = measured.get(name, {}).get('verdict') == 'same'
        if baseline and not executable(native):
            raise ValueError('non-executable oracle counted as baseline: ' + name)
        if reference['member']:
            labels = {'other:module member': None}
        elif name.rsplit('/', 1)[0] in member_dirs:
            labels = {'other:a module of several files': None}
        elif observation['ast_status']:
            labels = {'other:syntax refusal': None}
        else:
            labels = CurrentNeeds(censuslib.Tree(observation['ast']), prelude).run()
        inventory = dict(labels)
        if baseline:
            labels = {}
        elif not labels:
            code = scope.get('code') or []
            if code and code[0] == 'E0301':
                labels = {'resolution:trunk E0301': code[1:3]}
            else:
                what = scope.get('construct') or (code[3] if len(code) > 3 else 'lowered construct')
                labels = {'other:unmodelled ' + what: scope.get('at')}
        rows.append(dict(file=name, sha256=observation['sha256'], cls=scope['cls'], baseline=baseline,
                         native=native, lupin=reference['lupin']['verdict'],
                         labels=sorted(labels), families=sorted({family(label) for label in labels}),
                         sites=labels, model_needs=inventory, later_milestones=later_milestones(labels)))
    return rows


def later_milestones(labels):
    """Only explicit memory, module/generic/closure and host-call barriers.

    Unknown and ambiguous constructs are deliberately *not* barriers. Counting
    every other executable row as free gives an optimistic coverage ceiling,
    not a proposed change to any milestone's definition or completion bar.
    """
    found = []
    if any(label.startswith('mode:') or label in
           ('other:region', 'other:region value', 'other:in-region block',
            'other:prefix `copy`', 'other:prefix `move`', 'other:borrow') for label in labels):
        found.append('F3')
    if any(label in ('other:a module of several files', 'other:module member', 'other:`use`',
                     'other:generics', 'other:`trait`', 'other:`impl`', 'other:closure') for label in labels):
        found.append('F4')
    if any(label.startswith(('other:prelude `fs_', 'other:prelude `os_', 'other:prelude `env_')) for label in labels):
        found.append('F7')
    return found


def current_summary(rows):
    """Independent and joint gains above an execution-established baseline."""
    groups = {'baseline': [row['file'] for row in rows if row['baseline']]}
    candidates = [row for row in rows if not row['baseline'] and executable(row['native'])]
    for size in (1, 2, 3):
        for combo in itertools.combinations(('str', 'render', 'trap'), size):
            allowed = set(combo)
            groups['+'.join(combo)] = [row['file'] for row in candidates
                                      if row['families'] and set(row['families']) <= allowed]
    return groups


def classify(tree, prelude):
    return Needs(tree, prelude).run()


def census(binary, corpus, oracle, prelude, baseline):
    """Labels for every run row of the corpus, beside its census class and
    oracle verdicts. O(AST bytes) apart from invoking the parser."""
    import hashlib
    import json
    from pathlib import Path
    from differlib import corpus_rows
    corpus = Path(corpus)
    names = {e['name'] for e in json.loads(Path(prelude).read_text())['names']}
    recorded = {r['file']: r for r in json.loads(Path(oracle).read_text())['rows']}
    classes = {r['file']: r['cls'] for r in json.loads(Path(baseline).read_text())['rows']}
    entries = corpus_rows(corpus)
    member_dirs = {str(Path(r['file']).parent) for r in entries if r['member']}
    rows = []
    for entry in entries:
        if not (entry['expected'] or '').startswith('run('):
            continue
        source = corpus.parent / entry['file']
        observed = recorded[entry['file']]
        if observed['sha256'] != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError('stale oracle source: ' + entry['file'])
        if entry['member']:
            labels = {'other:module member': None}
        elif str(Path(entry['file']).parent) in member_dirs:
            labels = {'other:a module of several files': None}
        else:
            status, ast, _ = censuslib.run(binary, 'ast', source)
            if status not in (0, 2, 4):
                raise ValueError(f'parser crashed on {entry["file"]}: {status}')
            labels = {'other:syntax refusal': None} if status else classify(censuslib.Tree(ast.decode()), names)
        native = (observed.get('native_run') or observed['wolf'])['verdict']
        rows.append(dict(file=entry['file'], cls=classes[entry['file']], labels=sorted(labels),
                         families=sorted({family(l) for l in labels}), native=native,
                         lupin=observed['lupin']['verdict']))
    return rows


# Each family with the helpers it brings: a list's `for` also iterates ranges
# (one clause, mem.iter.for), and a map's pairs() yields tuples (type.map.key).
SCOPES = {'list': ('list', 'range'), 'map': ('map', 'tuple'), 'err': ('err',)}
CHOSEN = ('list', 'range', 'map', 'tuple', 'err')


def executable(verdict):
    return verdict.startswith(('exit(', 'trap('))


def summary(rows):
    """Run rows each family set brings into scope: the native oracle must
    run or trap (a native refusal is never predicted coverage), and the row
    must need something beyond the trunk compiler."""
    candidates = [r for r in rows if executable(r['native']) and r['families']]
    def reach(allowed):
        return [r['file'] for r in candidates if set(r['families']) <= set(allowed)]
    groups = {}
    for size in (1, 2, 3):
        for combo in itertools.combinations(SCOPES, size):
            allowed = sorted({f for name in combo for f in SCOPES[name]})
            groups['+'.join(combo)] = reach(allowed)
    chosen = set(CHOSEN)
    groups['also-strings'] = [r['file'] for r in candidates
                              if set(r['families']) <= chosen | {'str'} and 'str' in r['families']
                              and set(r['families']) & {'list', 'map', 'err'}]
    groups['also-modes'] = [r['file'] for r in candidates
                            if set(r['families']) <= chosen | {'mode'} and 'mode' in r['families']]
    groups['baseline'] = sorted(r['file'] for r in rows if r['cls'] == 'core')
    return groups
