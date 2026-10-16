"""Refill zones, run KiCad DRC, summarise by type (ignoring container-only library-table warnings)."""
import sys, re, pcbnew
from collections import Counter
path = sys.argv[1]
b = pcbnew.LoadBoard(path)
b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.WriteDRCReport(b, '/home/claude/gen/pcb/drc.rpt', pcbnew.EDA_UNITS_MILLIMETRES, True)
r = open('/home/claude/gen/pcb/drc.rpt').read()
c = Counter(); other = []
for blk in re.split(r'\n(?=\[)', r):
    m = re.match(r'\[(\w+)\]', blk)
    if not m: continue
    c[m.group(1)] += 1
    if m.group(1) not in ('lib_footprint_issues', 'unconnected_items'):
        other.append(blk)
print(dict(c))
print('\n'.join(other)[:4000])
if len(sys.argv) > 2:
    b.Save(sys.argv[2])
