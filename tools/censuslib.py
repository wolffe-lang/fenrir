"""The F1 core census: classify every corpus file from its AST dump, then hold
fenrir's typed verdict against the class and the recorded oracle.

The classifier here is independent of the checker: it reads `--emit=ast` text
and applies docs/TYPED.md's core extent with its own scoping. Classes, in order:
syntax-refused, out-of-core (module members and multi-file modules count here),
oracle-refused (core constructs only; the oracle rejects or refuses), core."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

TOKEN = re.compile(r'^token (\d+) (\S+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) "(.*)"$')
NODE = re.compile(r'^node (\d+) (\S+) (\d+) (-?\d+) (-?\d+) (-?\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$')
ESCAPES = {'\\': '\\', '"': '"', 'n': '\n', 'r': '\r', 't': '\t', '0': '\0'}
CORE_TYPES = {'int', 'bool', 'str', 'i32', 'i64', 'u8', 'u64', 'uint'}
CORE_FUNCTIONS = {'print', 'assert'}
EXPR_OUT = {'Tuple': 'tuple', 'List': 'list literal', 'FromEnd': 'from-end index', 'Cast': 'cast `as`',
            'Range': 'range', 'Default': '`else` default', 'Handler': '`else` handler', 'Index': 'index',
            'Receiver': 'moded receiver', 'Propagate': '`?` propagation', 'Match': '`match`',
            'Select': '`select`', 'Closure': 'closure', 'Region': 'region', 'RegionValue': 'region value',
            'InRegion': 'in-region block', 'Scope': '`scope`', 'Spawn': '`spawn`', 'When': '`when`',
            'Unsafe': '`unsafe`', 'InlineC': 'inline C', 'Asm': '`asm`', 'Borrow': 'borrow'}
ITEM_OUT = {'Enum': '`enum`', 'Trait': '`trait`', 'Impl': '`impl`', 'TypeAlias': 'type alias',
            'ErrorAlias': 'error alias', 'Use': '`use`', 'ImportC': '`import c`', 'Constant': '`const`',
            'ExternBinding': 'extern binding', 'Bindings': 'module binding'}
BINARY = {'+', '-', '*', '/', '%', '==', '!=', '<', '<=', '>', '>=', '&&', '||'}
ASSIGN = {'=', '+=', '-=', '*=', '/=', '%='}


def unescape(s):
    return re.sub(r'\\(.)', lambda m: ESCAPES[m.group(1)], s)


class Tree:
    def __init__(self, text):
        lines = text.splitlines()
        self.root = int(re.match(r'^ast/1 ".*" root=(\d+)$', lines[0]).group(1))
        self.tokens, self.nodes = [], []
        for line in lines[1:]:
            if line.startswith('token '):
                t = TOKEN.match(line)
                self.tokens.append((t.group(2), unescape(t.group(9))))
            else:
                n = NODE.match(line)
                self.nodes.append((n.group(2), int(n.group(3)), int(n.group(4)), int(n.group(6)),
                                   int(n.group(9)), int(n.group(10))))

    def kind(self, n): return self.nodes[n][0]
    def tok(self, n): return self.tokens[self.nodes[n][1]][0]
    def spell(self, n): return self.tokens[self.nodes[n][1]][1]
    def where(self, n): return [self.nodes[n][4], self.nodes[n][5]]

    def children(self, n):
        out, c = [], self.nodes[n][2]
        while c >= 0:
            out.append(c)
            c = self.nodes[c][3]
        return out


class Out(Exception):
    def __init__(self, what, node):
        super().__init__(what)
        self.what, self.node = what, node


class Classify:
    """First construct outside the F1 core, in source order, or None."""

    def __init__(self, tree, prelude):
        t = self.t = tree
        self.prelude = prelude
        self.fns, self.fallible, self.structs, self.fields = set(), set(), {}, set()
        for item in t.children(t.root):
            for d in t.children(item):
                if t.kind(d) == 'Function':
                    name = t.spell(next(c for c in t.children(d) if t.kind(c) == 'Name'))
                    self.fns.add(name)
                    for c in t.children(d):
                        if t.kind(c) == 'ReturnType':
                            ty = t.children(c)[0]
                            if t.kind(ty) == 'PrefixType' and t.spell(ty) == '!':
                                self.fallible.add(name)
                elif t.kind(d) == 'Struct':
                    cs = t.children(d)
                    fields = []
                    for c in cs:
                        if t.kind(c) == 'Fields':
                            for f in t.children(c):
                                fname = next(g for g in t.children(f) if t.kind(g) == 'Name')
                                ftype = [g for g in t.children(f) if t.kind(g) not in ('Name', 'Visibility', 'Attribute')]
                                fields.append((t.spell(fname), fname, ftype[0] if ftype else -1))
                                self.fields.add(t.spell(fname))
                    self.structs[t.spell(cs[0])] = (d, fields)
        self.scopes = []
        self.loops = 0
        self.tail = -1
        self.in_fallible = False
        self.resolving = False

    def run(self):
        # The checker's order: every syntactic judgment first, then the ones
        # that need names (resolution) and the struct graph.
        try:
            self.unit()
            self.resolving = True
            self.recursion()
            self.unit()
        except Out as o:
            return o.what, self.t.where(o.node)
        return None, None

    def recursion(self):
        t = self.t
        for name, (d, fields) in self.structs.items():
            seen = set()
            for fname, node, _ in fields:
                if fname in seen:
                    raise Out('a repeated field name', node)
                seen.add(fname)
        state = {}

        def visit(name):
            state[name] = 1
            for _, _, ty in self.structs[name][1]:
                if ty >= 0 and t.kind(ty) == 'NamedType':
                    target = t.spell(t.children(t.children(ty)[0])[0])
                    if target in self.structs:
                        if state.get(target) == 1:
                            raise Out('a recursive struct', self.structs[target][0])
                        if target not in state:
                            visit(target)
            state[name] = 2
        for name in self.structs:
            if name not in state:
                visit(name)

    def local(self, name):
        return any(name in scope for scope in self.scopes)

    def unit(self):
        t = self.t
        for c in t.children(t.root):
            if t.kind(c) == 'InnerAttribute':
                raise Out('attribute', c)
            for d in t.children(c):
                self.item(d)

    def item(self, d):
        t = self.t
        k = t.kind(d)
        if k == 'Attribute':
            raise Out('attribute', d)
        if k == 'Visibility':
            return
        if k in ITEM_OUT:
            raise Out(ITEM_OUT[k], d)
        if k == 'Function':
            self.function(d)
        elif k == 'Struct':
            self.struct(d)
        else:
            raise Out('item `%s`' % k, d)

    def function(self, n):
        t = self.t
        body = None
        params = set()
        self.in_fallible = False
        for c in t.children(n):
            k = t.kind(c)
            if k == 'Qualifier':
                raise Out('`%s` fn' % t.spell(c), c)
            if k == 'Generics':
                raise Out('generics', c)
            if k == 'Parameters':
                for p in t.children(c):
                    if t.kind(p) == 'Variadic':
                        raise Out('variadic', p)
                    for q in t.children(p):
                        kq = t.kind(q)
                        if kq == 'Mode':
                            raise Out('parameter mode `%s`' % t.spell(q), q)
                        if kq == 'ViewSet':
                            raise Out('view set', q)
                        if kq == 'Name':
                            if t.spell(q) == 'self':
                                raise Out('`self` receiver', q)
                            params.add(t.spell(q))
                        else:
                            self.type(q)
            elif k == 'ReturnType':
                ty = t.children(c)[0]
                if t.kind(ty) == 'PrefixType' and t.spell(ty) == '!':
                    self.in_fallible = True
                    self.type(t.children(ty)[0])
                else:
                    self.type(ty)
            elif k == 'Block':
                body = c
        if body is None:
            raise Out('bodyless fn', n)
        stmts = t.children(body)
        self.tail = -1
        if stmts and t.kind(stmts[-1]) == 'Tail':
            e = [x for x in t.children(stmts[-1]) if t.kind(x) != 'Attribute']
            self.tail = e[0] if e else -1
        self.scopes = [params]
        self.block(body)
        self.scopes = []

    def struct(self, n):
        t = self.t
        for c in t.children(n):
            if t.kind(c) == 'Generics':
                raise Out('generics', c)
            if t.kind(c) == 'Fields':
                for f in t.children(c):
                    for g in t.children(f):
                        kg = t.kind(g)
                        if kg == 'Attribute':
                            raise Out('attribute', g)
                        if kg not in ('Visibility', 'Name'):
                            self.type(g)

    def type(self, n):
        t = self.t
        k = t.kind(n)
        if k == 'NamedType':
            cs = t.children(n)
            if len(cs) > 1:
                raise Out('generic type `%s`' % t.spell(t.children(cs[0])[0]), n)
            names = t.children(cs[0])
            if len(names) != 1:
                raise Out('qualified type', n)
            name = t.spell(names[0])
            if self.resolving and name not in self.structs and name not in self.fns and name in self.prelude and name not in CORE_TYPES:
                raise Out('type `%s`' % name, names[0])
            return
        if k == 'TupleType':
            if t.children(n):
                raise Out('tuple type', n)
            return
        if k in ('PrefixType', 'BuiltinType'):
            raise Out('`%s` type' % t.spell(n), n)
        raise Out({'ErrorType': 'error row type', 'FunctionType': 'fn type'}.get(k, 'type `%s`' % k), n)

    def block(self, n):
        t = self.t
        self.scopes.append(set())
        for st in t.children(n):
            for d in t.children(st):
                k = t.kind(d)
                if k == 'Attribute':
                    raise Out('attribute', d)
                if t.kind(st) == 'Tail':
                    self.expr(d)
                elif k == 'Item':
                    decls = [x for x in t.children(d) if t.kind(x) != 'Visibility']
                    for x in decls:
                        if t.kind(x) == 'Attribute':
                            raise Out('attribute', x)
                        if t.kind(x) != 'Bindings':
                            raise Out('nested item', x)
                        self.bindings(x)
                elif k == 'Assignment':
                    self.assignment(d)
                elif k == 'Defer':
                    raise Out('`%s`' % t.spell(d), d)
                elif k == 'Assume':
                    raise Out('`assume`', d)
                else:
                    self.expr(d)
        self.scopes.pop()

    def bindings(self, n):
        t = self.t
        cs = t.children(n)
        if t.spell(cs[0]) == 'const':
            raise Out('`const`', cs[0])
        for b in cs[1:]:
            parts = t.children(b)
            pat = parts[0]
            kp = t.kind(pat)
            if kp == 'NamePattern':
                if len(t.children(t.children(pat)[0])) != 1:
                    raise Out('qualified pattern', pat)
            elif kp != 'WildcardPattern':
                raise Out('pattern `%s`' % kp, pat)
            for q in parts[1:-1]:
                self.type(q)
            self.expr(parts[-1])
            if kp == 'NamePattern':
                self.scopes[-1].add(t.spell(t.children(t.children(pat)[0])[0]))

    def assignment(self, n):
        t = self.t
        cs = t.children(n)
        self.expr(cs[0])
        if t.kind(cs[0]) not in ('Name', 'Member'):
            raise Out('assignment place', cs[0])
        if t.spell(cs[1]) not in ASSIGN:
            raise Out('assignment `%s`' % t.spell(cs[1]), cs[1])
        for c in cs[2:]:
            if t.kind(c) == 'Mode':
                raise Out('moded store', c)
            self.expr(c)

    def name(self, n, call):
        t = self.t
        name = t.spell(n)
        if not self.resolving:
            return
        if self.local(name):
            return
        if name in self.fns or name in self.structs:
            if name in self.structs:
                raise Out('a type used as a value', n)
            if not call:
                raise Out('a function used as a value', n)
            return
        if name in self.prelude:
            if name in CORE_TYPES:
                raise Out('a type used as a value', n)
            if name not in CORE_FUNCTIONS:
                raise Out('prelude `%s`' % name, n)
            if not call:
                raise Out('a function used as a value', n)
            return
        if self.in_fallible and (n == self.tail or getattr(self, 'returning', -1) == n):
            raise Out('error tag `%s`' % name, n)

    def expr(self, n):
        t = self.t
        k = t.kind(n)
        if k in EXPR_OUT:
            raise Out(EXPR_OUT[k], n)
        if k == 'Name':
            self.name(n, False)
            return
        if k == 'Literal':
            if t.tok(n) not in ('int', 'true', 'false', 'raw'):
                raise Out('%s literal' % t.tok(n), n)
            return
        if k == 'String':
            multi = t.tok(n) == 'multi-open'
            for c in t.children(n):
                if t.kind(c) == 'Interpolation':
                    if multi:
                        raise Out('interpolation in a multiline string', c)
                    parts = t.children(c)
                    if len(parts) > 1:
                        raise Out('format spec', parts[1])
                    self.expr(parts[0])
            return
        if k == 'Group':
            self.expr(t.children(n)[0])
            return
        if k == 'Prefix':
            cs = t.children(n)
            op = t.spell(cs[0])
            if op not in ('-', '!') or t.kind(cs[1]) == 'Mode':
                raise Out('prefix `%s`' % op, n)
            self.expr(cs[1])
            return
        if k == 'Binary':
            a, op, b = t.children(n)
            self.expr(a)
            if t.spell(op) not in BINARY:
                raise Out('operator `%s`' % t.spell(op), op)
            self.expr(b)
            return
        if k == 'Call':
            recv, args = t.children(n)
            kr = t.kind(recv)
            if kr == 'Member':
                raise Out('method call', n)
            if kr == 'Index':
                raise Out('generic application', n)
            if kr != 'Name':
                raise Out('call of a computed value', n)
            self.name(recv, True)
            for a in t.children(args):
                v = t.children(a)[0]
                if t.kind(v) == 'Mode':
                    raise Out('argument mode `%s`' % t.spell(v), v)
                self.expr(v)
            if self.resolving and not self.local(t.spell(recv)) and t.spell(recv) in self.fallible:
                raise Out('a call of a fallible function', n)
            return
        if k == 'StructLiteral':
            cs = t.children(n)
            if t.kind(cs[0]) != 'Name':
                raise Out('qualified struct literal', cs[0])
            for f in cs[1:]:
                parts = t.children(f)
                if len(parts) > 1:
                    self.expr(parts[1])
                else:
                    self.name(parts[0], False)
            return
        if k == 'Member':
            recv, member = t.children(n)
            self.expr(recv)
            if t.tok(member) == 'int':
                raise Out('tuple index', member)
            if self.resolving and t.spell(member) not in self.fields:
                raise Out('member `%s`' % t.spell(member), member)
            return
        if k == 'If':
            for c in t.children(n):
                self.block(c) if t.kind(c) == 'Block' else self.expr(c)
            return
        if k == 'Block':
            self.block(n)
            return
        if k == 'Loop':
            cs = t.children(n)
            if t.spell(cs[0]) != 'while':
                raise Out('`%s` loop' % t.spell(cs[0]), n)
            self.expr(cs[1])
            self.loops += 1
            self.block(cs[2])
            self.loops -= 1
            return
        if k == 'Jump':
            cs = t.children(n)
            word = t.spell(cs[0])
            if word != 'return':
                if len(cs) > 1:
                    raise Out('`%s` value' % word, n)
                if self.loops == 0 and self.resolving:
                    raise Out('`%s` outside a loop' % word, n)
                return
            if len(cs) > 1:
                self.returning = cs[1]
                self.expr(cs[1])
                self.returning = -1
            return
        raise Out('expression `%s`' % k, n)


def run(binary, mode, path, timeout=30):
    r = subprocess.run([str(binary), '--emit=' + mode, str(path)], capture_output=True, timeout=timeout)
    text = r.stderr.decode(errors='replace')
    code = re.search(r':(\d+):(\d+): error\[([A-Z0-9]+)\]', text)
    named = re.search(r'not yet in fenrir: (.*) \(bytes \d+\.\.\d+\)$', text, re.M)
    found = [code.group(3), int(code.group(1)), int(code.group(2))] if code else None
    if found and named:
        found.append(named.group(1))
    return r.returncode, r.stdout, found


def position(data, offset):
    prefix = data[:offset].decode(errors='replace')
    return [prefix.count('\n') + 1, len(prefix) - (prefix.rfind('\n') + 1) + 1]


def oracle_site(row, data):
    """The line:column of the recorded native rejection's first error, or None."""
    record = ((row.get('native_run') or {}).get('classification_observation') or {}).get('record') or {}
    errors = [d for d in record.get('diagnostics', []) if d.get('severity') == 'error']
    if not errors:
        return None
    return position(data, min(errors, key=lambda d: d['span'][0])['span'][0])


def oracle_verdict(row):
    """The recorded native wolf answer: accepted, or refused with a code or none."""
    native = row.get('native_run') or {}
    verdict = native.get('verdict', row['wolf']['verdict'])
    if verdict.startswith('fail('):
        return 'refused', verdict[5:-1]
    if verdict == 'unsupported':
        declared = (row.get('declared_phase') or {}).get('wolf', {}).get('verdict')
        if (row.get('expected') or '').startswith('pass') and declared == 'pass':
            return 'accepted', None
        return 'refused', None
    if verdict in ('tool-error', 'timeout', 'crash'):
        return 'refused', None
    return 'accepted', None


def scope_blocker(tree, names):
    """The core extension fenrir implements: F1, enums and `match` (predictlib),
    then lists, `Map`, tuples, ranges in `for` and error rows (needslib). The
    first label outside that scope, by source position, or (None, None)."""
    import needslib
    from predictlib import Implemented
    labels = needslib.Needs(tree, names).run()
    # An enum interpolated into a string is refused when lowering, not typing.
    outside = sorted((at, label) for label, at in labels.items()
                     if needslib.family(label) not in needslib.CHOSEN and label != 'str:rendered in a string')
    if outside:
        return outside[0][1].split(':', 1)[1], outside[0][0]
    # Within the families, the enum and match refusals fenrir keeps by name.
    construct, where = Implemented(tree, names).run()
    if construct == 'an or-pattern that binds names':
        return construct, where
    return None, None


def census(binary, corpus, oracle, prelude):
    names = {e['name'] for e in json.loads(Path(prelude).read_text())['names']}
    recorded = {row['file']: row for row in json.loads(Path(oracle).read_text())['rows']}
    rows = []
    sources = sorted(Path(corpus).rglob('*.lu'))
    member_dirs = set()
    from differlib import corpus_rows
    from predictlib import Implemented
    listed = corpus_rows(Path(corpus))
    for entry in listed:
        if entry['member']:
            member_dirs.add(str(Path(entry['file']).parent))
    for entry, source in zip(listed, sources):
        assert entry['file'] == source.relative_to(Path(corpus).parent).as_posix(), 'enumeration order'
        o = recorded[entry['file']]
        assert o['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest(), 'oracle table is stale'
        ast_status, ast_out, ast_code = run(binary, 'ast', source)
        typed_status, _, typed_code = run(binary, 'typed', source)
        construct, where, extended, beyond = None, None, None, None
        if ast_status == 0:
            tree = Tree(ast_out.decode())
            construct, where = Classify(tree, names).run()
            if construct is not None:
                extended, beyond = scope_blocker(tree, names)
        verdict, code = ('member', None) if entry['member'] else oracle_verdict(o)
        oracle_at = oracle_site(o, source.read_bytes()) if verdict == 'refused' else None
        if ast_status != 0:
            cls = 'syntax-refused'
        elif entry['member']:
            cls, construct, where = 'out-of-core', 'module member', None
        elif str(Path(entry['file']).parent) in member_dirs:
            cls, construct, where = 'out-of-core', 'a module of several files', None
        elif construct is not None and extended is not None:
            cls, construct, where = 'out-of-core', extended, beyond
        elif verdict == 'refused':
            cls = 'oracle-refused'
        else:
            # F1 with enums and `match`, lists, maps, tuples and rows.
            cls, construct, where = 'core', None, None
        rows.append(dict(file=entry['file'], sha256=o['sha256'], cls=cls, construct=construct, at=where,
                         oracle=verdict, oracle_code=code, oracle_at=oracle_at, ast=ast_status, typed=typed_status,
                         code=typed_code))
    return rows


def gate(rows):
    """Every failed condition, by row. An empty list is a pass."""
    problems = []
    for r in rows:
        status = r['typed']
        code = r['code'][0] if r['code'] else None
        if r['ast'] not in (0, 2) or status not in (0, 2, 4):
            problems.append(f'{r["file"]}: fenrir crashed (ast={r["ast"]} typed={status})')
        elif r['cls'] == 'syntax-refused' and status != 2:
            problems.append(f'{r["file"]}: syntax refusal not kept by the typed view')
        elif r['construct'] == 'module member':
            # A member is compiled through its package's entry and never on its
            # own; fenrir's standalone view of it need only not crash.
            continue
        elif r['cls'] == 'out-of-core':
            like_oracle = r['oracle'] == 'refused' and code is not None and code == r['oracle_code']
            if not (status == 4 and code == 'F0001') and not like_oracle:
                problems.append(f'{r["file"]}: outside the core ({r["construct"]}) but typed status {status} {code}')
        elif r['cls'] == 'core' and status != 0:
            problems.append(f'{r["file"]}: core row refused: {r["code"]}')
        elif r['cls'] == 'oracle-refused' and status != 0 and r['oracle_code'] is not None:
            if code != r['oracle_code'] or r['code'][1:] != r['oracle_at']:
                problems.append(f'{r["file"]}: refused with {r["code"]}, the oracle with {r["oracle_code"]} at {r["oracle_at"]}')
    return problems


def counts(rows):
    c = {name: sum(r['cls'] == name for r in rows) for name in ('core', 'oracle-refused', 'out-of-core', 'syntax-refused')}
    refused = [r for r in rows if r['cls'] == 'oracle-refused']
    c['oracle-refused-fenrir-accepts'] = sum(r['typed'] == 0 for r in refused)
    c['oracle-refused-same-code'] = sum(bool(r['typed'] != 0 and r['code'] and r['code'][0] == r['oracle_code']) for r in refused)
    outside = [r for r in rows if r['cls'] == 'out-of-core']
    c['out-of-core-f0001'] = sum(r['typed'] == 4 for r in outside)
    c['out-of-core-refused-like-oracle'] = sum(r['typed'] == 2 for r in outside)
    named = [r for r in outside if r['typed'] == 4 and r['at'] is not None]
    c['out-of-core-same-construct-and-site'] = sum(r['code'][3:] == [r['construct']] and r['code'][1:3] == r['at'] for r in named)
    c['out-of-core-classified-by-node'] = len(named)
    c['files'] = len(rows)
    return c


def table(rows, identity):
    histogram = {}
    for r in rows:
        if r['cls'] == 'out-of-core':
            histogram[r['construct']] = histogram.get(r['construct'], 0) + 1
    first = sorted(histogram.items(), key=lambda kv: (-kv[1], kv[0]))
    return dict(format=1, identity=identity, counts=counts(rows), constructs=[[k, v] for k, v in first], rows=rows)
