"""Apply a Freerouting .ses to the working board, refill zones, DRC, and score."""
import sys, re, pcbnew, shutil
from collections import Counter
ses, out = sys.argv[1], sys.argv[2]
BASE = __import__('os').environ.get('BASE', 'base'); shutil.copy(BASE + '.kicad_pcb', out); shutil.copy(BASE + '.kicad_pro', out.replace('.kicad_pcb', '.kicad_pro'))
shutil.copy('base.kicad_dru', out.replace('.kicad_pcb', '.kicad_dru'))
b = pcbnew.LoadBoard(out)
from ses_apply import apply_ses; apply_ses(b, ses)
# drop exact duplicates (the .ses repeats the locked pre-routes)
seen = set(); dups = 0
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition(); key = ('V', p.x, p.y, t.GetNetCode())
    else:
        s0, e0 = t.GetStart(), t.GetEnd()
        a, c = sorted([(s0.x, s0.y), (e0.x, e0.y)])
        key = ('T', a, c, t.GetLayer(), t.GetNetCode(), t.GetWidth())
    if key in seen:
        if not t.IsLocked():
            b.Remove(t); dups += 1
    else:
        seen.add(key)
print('   removed duplicates:', dups)
b.BuildConnectivity()
# remove dangling stubs left by the router (repeat until none)
removed = 0
while True:
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    dang = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and
            conn.TestTrackEndpointDangling(t, False)]
    if not dang: break
    for t in dang: b.Remove(t); removed += 1
print('   removed dangling segments:', removed)
b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(out)
rpt = out.replace('.kicad_pcb', '.drc.rpt')
pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
r = open(rpt).read()
c = Counter(); unc = Counter(); other = []
for blk in re.split(r'\n(?=\[)', r):
    m = re.match(r'\[(\w+)\]', blk)
    if not m: continue
    if m.group(1) == 'lib_footprint_issues': continue
    c[m.group(1)] += 1
    if m.group(1) == 'unconnected_items':
        for n in re.findall(r'\[([^\]]+)\]', blk.split('\n', 1)[1])[:1]: unc[n] += 1
    else:
        other.append(blk.strip().split('\n')[0] + ' | ' + ' / '.join(l.strip() for l in blk.strip().split('\n')[2:4]))
tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
L = Counter()
for t in tracks: L[pcbnew.LayerName(t.GetLayer())] += pcbnew.ToMM(t.GetLength())
print(f'{ses}: violations={dict(c)} vias={len(vias)} track_mm F={L["F.Cu"]:.0f} B={L["B.Cu"]:.0f}')
if unc: print('   unconnected by net:', dict(unc))
for o in other[:12]: print('   ', o)
