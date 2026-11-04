"""Linear lexical construct inventory, deliberately not a Wolf parser.

Each token is classified once. Interpolated strings are a conservative lexical
union, not parsed expressions. Comments and strings use monotone cursors.
"""
from collections import Counter
from pathlib import Path

KEYWORDS = set('as asm assert atomic break case catch closed comptime const continue copy defer distinct else enum errdefer error export extern false fn for if impl import in let loop match move mut new nil noalloc opaque par proc pub read region return scope select self shared spawn struct super take task this thread trait true try type unsafe use var when while with yield'.split())
OPERATORS = ('<<=', '>>=', '...', '..=', '->', '=>', '==', '!=', '<=', '>=', '&&', '||', '<<', '>>', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '..', '::')


def lex(text):
    tokens = []
    n = len(text)
    i = 0
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if text.startswith('//', i):
            at = text.find('\n', i + 2)
            i = n if at < 0 else at
            continue
        if text.startswith('/*', i):
            depth = 1
            i += 2
            while i < n and depth:
                if text.startswith('/*', i):
                    depth += 1
                    i += 2
                elif text.startswith('*/', i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            if depth:
                tokens.append(('unknown:unclosed-comment', '/*'))
            continue
        start = i
        if c == 'r':
            j = i + 1
            while j < n and text[j] == '#':
                j += 1
            if j < n and text[j] == '"':
                close = '"' + text[i + 1:j]
                at = text.find(close, j + 1)
                i = n if at < 0 else at + len(close)
                tokens.append(('literal:raw-string' if at >= 0 else 'unknown:unclosed-string', text[start:i]))
                continue
        if c in ('"', "'"):
            quote = '"""' if text.startswith('"""', i) else c
            kind = 'literal:multiline-string' if len(quote) == 3 else ('literal:string' if c == '"' else 'literal:character')
            i += len(quote)
            escaped = False
            while i < n:
                if not escaped and text.startswith(quote, i):
                    i += len(quote)
                    break
                if text[i] == '\\' and not escaped:
                    escaped = True
                else:
                    escaped = False
                i += 1
            else:
                kind = 'unknown:unclosed-string'
            value = text[start:i]
            tokens.append((kind, value))
            if c == '"':
                # Classify interpolation presence, not the grammar inside it. The
                # full string-interpolation construct is conservatively indivisible.
                j = len(quote)
                while j < len(value) - len(quote):
                    if value[j] == '\\':
                        j += 2
                    elif value.startswith('{{', j) or value.startswith('}}', j):
                        j += 2
                    elif value[j] == '{':
                        tokens.append(('string-interpolation', '{'))
                        j += 1
                    else:
                        j += 1
            continue
        if c.isalpha() or c == '_':
            i += 1
            while i < n and (text[i].isalnum() or text[i] == '_'):
                i += 1
            value = text[start:i]
            tokens.append(('keyword:' + value if value in KEYWORDS else 'identifier', value))
            if i < n and text[i] == '"':
                tokens.append(('generalized-string-prefix', value))
            continue
        if c.isdigit():
            i += 1
            while i < n and (text[i].isalnum() or text[i] == '_'):
                i += 1
            kind = 'literal:integer'
            if i + 1 < n and text[i] == '.' and text[i + 1].isdigit():
                kind = 'literal:float'
                i += 1
                while i < n and (text[i].isalnum() or text[i] in '_+-'):
                    i += 1
            elif any(x in text[start:i] for x in ('e', 'E')) and not text[start:i].lower().startswith(('0x', '0b', '0o')):
                kind = 'literal:float'
            tokens.append((kind, text[start:i]))
            continue
        operator = next((op for op in OPERATORS if text.startswith(op, i)), c)
        i += len(operator)
        if operator in ('(', ')', '{', '}', ',', ':', ';'):
            kind = 'delimiter:' + {'(': 'parentheses', ')': 'parentheses', '{': 'braces', '}': 'braces', ',': 'comma', ':': 'colon', ';': 'semicolon'}[operator]
        elif operator in ('[', ']'):
            kind = 'brackets:generic-or-index-or-list'
        elif operator == '.':
            kind = 'member-or-method'
        elif operator in ('..', '..=', '...'):
            kind = 'operator:range-or-rest'
        elif operator in ('->', '=>'):
            kind = 'operator:arrow'
        elif operator in ('!', '?'):
            kind = 'operator:error-or-negation' if operator == '!' else 'operator:propagate'
        elif operator in ('+', '-', '*', '/', '%'):
            kind = 'operator:arithmetic-or-pointer'
        elif operator in ('=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>='):
            kind = 'operator:assignment'
        elif operator in ('==', '!=', '<', '>', '<=', '>='):
            kind = 'operator:comparison'
        elif operator in ('&&', '||'):
            kind = 'operator:logical'
        elif operator in ('&', '|', '^', '~', '<<', '>>'):
            kind = 'operator:bitwise-or-closure-or-reference'
        elif operator in ('#', '@', '::'):
            kind = 'attribute-or-qualified-name'
        else:
            kind = 'unknown:' + operator
        tokens.append((kind, operator))
    return tokens


def inventory(source):
    result = Counter()
    for path in sorted(Path(source).rglob('*.lu')):
        result.update(kind for kind, _ in lex(path.read_text()))
    return result
