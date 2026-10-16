"""Minimal S-expression reader/writer for KiCad files."""
import re

class Sym(str):
    """Bare atom (not quoted)."""
    pass

_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)

def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError('parse error at %d: %r' % (pos, text[pos:pos+40]))
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            node = stack.pop()
            stack[-1].append(node)
        elif m.group(3) is not None:
            s = re.sub(r'\\(.)', lambda mm: {'n': '\n', 't': '\t'}.get(mm.group(1), mm.group(1)), m.group(3))
            stack[-1].append(s)
        else:
            stack[-1].append(Sym(m.group(4)))
    return stack[0]

def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

def dump(node, indent=0):
    if isinstance(node, list):
        parts = [dump(c, indent + 1) for c in node]
        one = '(' + ' '.join(parts) + ')'
        if len(one) + indent * 2 < 100 and '\n' not in one:
            return one
        out = '(' + parts[0]
        for p in parts[1:]:
            out += '\n' + '  ' * (indent + 1) + p
        return out + '\n' + '  ' * indent + ')'
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, (int, float)):
        return fmt(node)
    return q(node)

def fmt(v):
    if isinstance(v, int):
        return str(v)
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s
