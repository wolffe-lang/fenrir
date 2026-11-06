"""Predict the core-plus-enum/match frontier without teaching the compiler it.

Uses the ordinary census AST interface and F1 classifier. Only enums and match
patterns over F1 values are added: no tuple, list, mode, error row or other
feature is smuggled in through a payload or arm. This is a scope prediction,
not a type checker, exhaustiveness checker, or claim of successful execution.
Spec: gram.item.type, gram.expr.variant, gram.expr.flow, gram.pat and abi.native.enum.
"""
import hashlib
import json
from pathlib import Path

import censuslib
from censuslib import Out
from differlib import corpus_rows


class Classify(censuslib.Classify):
    def __init__(self, tree, prelude):
        super().__init__(tree, prelude)
        self.features = set()
        self.enums = {}
        for item in tree.children(tree.root):
            for decl in tree.children(item):
                children = tree.children(decl)
                variants = [c for c in children if tree.kind(c) == 'Variants']
                if tree.kind(decl) in ('Enum', 'TypeAlias') and variants:
                    name = next(c for c in children if tree.kind(c) == 'Name')
                    self.enums[tree.spell(name)] = (decl, variants[0])
        self.enum_nodes = {decl for decl, _ in self.enums.values()}

    def item(self, n):
        t = self.t
        if n not in self.enum_nodes:
            return super().item(n)
        self.features.add('enum')
        for c in t.children(n):
            if t.kind(c) == 'Generics':
                raise Out('generics', c)
            if t.kind(c) == 'Variants':
                for variant in t.children(c):
                    for payload in t.children(variant)[1:]:
                        self.type(payload)

    def type(self, n):
        t = self.t
        children = t.children(n)
        if t.kind(n) == 'NamedType' and len(children) == 1:
            names = t.children(children[0])
            if len(names) == 1 and t.spell(names[0]) in self.enums:
                return
        super().type(n)

    def recursion(self):
        super().recursion()
        t = self.t
        aggregates = {name: (decl, [ty for _, _, ty in fields])
                      for name, (decl, fields) in self.structs.items()}
        for name, (decl, variants) in self.enums.items():
            aggregates[name] = (decl, [ty for v in t.children(variants) for ty in t.children(v)[1:]])
        state = {}
        def visit(name):
            state[name] = 1
            for ty in aggregates[name][1]:
                if ty < 0 or t.kind(ty) != 'NamedType':
                    continue
                target = t.spell(t.children(t.children(ty)[0])[0])
                if target in aggregates:
                    if state.get(target) == 1:
                        raise Out('a recursive aggregate', aggregates[target][0])
                    if target not in state:
                        visit(target)
            state[name] = 2
        for name in aggregates:
            if name not in state:
                visit(name)

    def constructor(self, n):
        t = self.t
        if t.kind(n) != 'Member':
            return False
        receiver, _ = t.children(n)
        return (t.kind(receiver) == 'Name' and t.spell(receiver) in self.enums
                and not self.local(t.spell(receiver)))

    def pattern(self, n):
        t = self.t
        k, children = t.kind(n), t.children(n)
        if k == 'WildcardPattern':
            return set()
        if k == 'NamePattern':
            names = t.children(children[0])
            # The classifier does not infer the scrutinee type. A bare name may
            # bind; recording it as in scope cannot invent a new language form.
            return {t.spell(names[0])} if len(names) == 1 else set()
        if k == 'LiteralPattern':
            self.expr(children[0])
            return set()
        if k == 'RangePattern':
            self.expr(children[0]); self.expr(children[2])
            return set()
        if k == 'AtPattern':
            return {t.spell(t.children(children[0])[0])} | self.pattern(children[1])
        if k == 'StructPattern':
            bound = set()
            for field in children[1:]:
                if t.kind(field) == 'RestPattern':
                    continue
                parts = t.children(field)
                bound |= self.pattern(parts[1]) if len(parts) > 1 else {t.spell(parts[0])}
            return bound
        if k in ('ConstructorPattern', 'OrPattern'):
            bound = set()
            for part in children[1:] if k == 'ConstructorPattern' else children:
                bound |= self.pattern(part)
            return bound
        raise Out('pattern `%s`' % k, n)

    def expr(self, n):
        t = self.t
        if t.kind(n) == 'Match':
            self.features.add('match')
            children = t.children(n)
            self.expr(children[0])
            for arm in children[1:]:
                parts = t.children(arm)
                bindings = self.pattern(parts[0])
                self.scopes.append(bindings)
                for part in parts[1:]:
                    self.expr(t.children(part)[0] if t.kind(part) == 'Guard' else part)
                self.scopes.pop()
            return
        if self.constructor(n):
            self.features.add('enum')
            return
        if t.kind(n) == 'Call':
            receiver, arguments = t.children(n)
            if self.constructor(receiver):
                self.features.add('enum')
                for argument in t.children(arguments):
                    value = t.children(argument)[0]
                    if t.kind(value) == 'Mode':
                        raise Out('argument mode `%s`' % t.spell(value), value)
                    self.expr(value)
                return
        super().expr(n)


class Implemented(Classify):
    """The extension as fenrir implements it, for the census: also outside, as
    fenrir refuses it by name, is an or-pattern whose alternatives bind names.
    A bare name that some enum of the file declares as a variant is taken as
    that constructor, since the classifier does not infer scrutinee types."""

    def __init__(self, tree, prelude):
        super().__init__(tree, prelude)
        self.variant_names = {tree.spell(tree.children(v)[0])
                              for _, variants in self.enums.values() for v in tree.children(variants)}

    def pattern(self, n):
        bound = super().pattern(n)
        if self.t.kind(n) == 'OrPattern' and bound - self.variant_names:
            raise Out('an or-pattern that binds names', n)
        return bound


def executable(verdict):
    return verdict.startswith(('exit(', 'trap('))


def summary(rows):
    native = [r for r in rows if r['within'] and r['run'] and executable(r['native'])]
    return dict(baseline_native=[r['file'] for r in native if r['baseline']],
                new_native_same=[r['file'] for r in native if not r['baseline']],
                interpreter_parity=[r['file'] for r in native],
                reference_interpreter_only=[r['file'] for r in rows
                    if r['within'] and r['run'] and not executable(r['native']) and executable(r['lupin'])])


def census(binary, corpus, oracle, prelude, baseline):
    """O(AST bytes plus aggregate edges), apart from invoking the parser."""
    corpus = Path(corpus)
    names = {e['name'] for e in json.loads(Path(prelude).read_text())['names']}
    recorded = {r['file']: r for r in json.loads(Path(oracle).read_text())['rows']}
    old = json.loads(Path(baseline).read_text())
    core = {r['file'] for r in old['rows'] if r['cls'] == 'core'}
    entries = corpus_rows(corpus)
    member_dirs = {str(Path(r['file']).parent) for r in entries if r['member']}
    rows = []
    for index, entry in enumerate(entries):
        source = corpus.parent / entry['file']
        observed = recorded[entry['file']]
        if observed['sha256'] != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError('stale oracle source: ' + entry['file'])
        status, ast, _ = censuslib.run(binary, 'ast', source)
        if status not in (0, 2, 4):
            raise ValueError(f'parser crashed on {entry["file"]}: {status}')
        features = []
        if status:
            blocker, at = 'syntax refusal', None
        elif entry['member']:
            blocker, at = 'module member', None
        elif str(Path(entry['file']).parent) in member_dirs:
            blocker, at = 'a module of several files', None
        else:
            classifier = Classify(censuslib.Tree(ast.decode()), names)
            blocker, at = classifier.run()
            features = sorted(classifier.features)
        rows.append(dict(file=entry['file'], sha256=observed['sha256'],
                         within=blocker is None, blocker=blocker, at=at,
                         run=(entry['expected'] or '').startswith('run('),
                         baseline=entry['file'] in core, features=features,
                         native=(observed.get('native_run') or observed['wolf'])['verdict'],
                         lupin=observed['lupin']['verdict']))
        if (index + 1) % 100 == 0:
            print(f'prediction: classified {index + 1}/{len(entries)}', flush=True)
    groups = summary(rows)
    if set(groups['baseline_native']) != core:
        raise ValueError('prediction lost an existing core row')
    return dict(format=1, scope='F1 plus non-generic enums and match over F1 values',
                baseline_identity=old['identity'],
                counts={key: len(value) for key, value in groups.items()},
                groups=groups, rows=rows)
