"""Check a KiCad 10 schematic: pin positions vs the generated design, wires/labels intact, footprints."""
import json, math, sys
from sexp import parse
from gen_sch import rot, snap, sym_pins  # reuse geometry helpers (importing runs the generator in-memory only)

path = sys.argv[1]
root = parse(open(path).read())[0]
libs = {n[1]: n for n in [x for x in root if isinstance(x, list) and x and x[0] == 'lib_symbols'][0][1:]}
placed = [n for n in root if isinstance(n, list) and n and n[0] == 'symbol']
before = json.load(open('/home/claude/gen/out/pinmap.json'))

def get(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
mism = 0; fps = {}
for s in placed:
    lib_id = get(s, 'lib_id')[1]
    at = get(s, 'at'); x, y, r = float(at[1]), float(at[2]), int(float(at[3]))
    ref = [c[2] for c in s if isinstance(c, list) and c and c[0] == 'property' and c[1] == 'Reference'][0]
    fp = [c[2] for c in s if isinstance(c, list) and c and c[0] == 'property' and c[1] == 'Footprint'][0]
    if get(s, 'mirror'): print('MIRROR on', ref)
    if not ref.startswith('#'): fps[ref] = fp
    now = {}
    for p in sym_pins(libs[lib_id]):
        dx, dy = rot(p['x'], -p['y'], r)
        now.setdefault(p['num'], [snap(x + dx), snap(y + dy)])
    old = before[ref]
    for num in set(now) | set(old):
        if num not in now or num not in old or abs(now[num][0]-old[num][0]) > 0.01 or abs(now[num][1]-old[num][1]) > 0.01:
            mism += 1; print('PIN MOVED/CHANGED', ref, num, old.get(num), now.get(num))
print('placed symbols:', len(placed), ' pin mismatches:', mism)
print('parts with empty footprint:', [r for r, f in fps.items() if not f])
counts = {k: sum(1 for n in root if isinstance(n, list) and n and n[0] == k) for k in ('wire', 'label', 'no_connect', 'junction', 'text', 'rectangle')}
print('items:', counts)
