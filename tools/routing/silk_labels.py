"""Find the nearest clear spot for each top-silkscreen label that touches copper or other silkscreen."""
import pcbnew, math, json
b = pcbnew.LoadBoard('/home/claude/route/p1.kicad_pcb')
OX = OY = 100.0
FM = pcbnew.FromMM; MM = pcbnew.ToMM
def box(bb, inflate=0.0):
    x0, y0 = MM(bb.GetLeft()) - inflate, MM(bb.GetTop()) - inflate
    return (x0, y0, MM(bb.GetRight()) + inflate, MM(bb.GetBottom()) + inflate)
def hit(a, c): return not (a[2] <= c[0] or c[2] <= a[0] or a[3] <= c[1] or c[3] <= a[1])
copper = []
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        copper.append(box(t.GetBoundingBox(), 0.15))
    elif t.GetLayer() == pcbnew.F_Cu:
        # sample along the track so diagonal tracks don't block their whole bounding box
        s, e = t.GetStart(), t.GetEnd(); w = MM(t.GetWidth()) / 2 + 0.15
        n = max(1, int(MM(t.GetLength()) / 0.25))
        for i in range(n + 1):
            x = MM(s.x) + (MM(e.x) - MM(s.x)) * i / n; y = MM(s.y) + (MM(e.y) - MM(s.y)) * i / n
            copper.append((x - w, y - w, x + w, y + w))
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.IsOnLayer(pcbnew.F_Cu) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            copper.append(box(p.GetBoundingBox(), 0.15))
silk_graphics = []
for fp in b.GetFootprints():
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != 'FP_TEXT':
            silk_graphics.append((fp.GetReference(), box(g.GetBoundingBox(), 0.1)))
labels = []
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS:
        labels.append(('text', d.GetText(), d))
for fp in b.GetFootprints():
    r = fp.Reference()
    if r.IsVisible() and r.GetLayer() == pcbnew.F_SilkS:
        labels.append(('ref', fp.GetReference(), r))
edge = (0.6, 0.6, 59.4, 59.4)
keepout = (6.0, 0.0, 54.0, 6.6)   # antenna strip: keep labels off it too
def clear(lbox, me, others):
    x0, y0, x1, y1 = lbox
    if x0 < OX + edge[0] or y0 < OY + edge[1] or x1 > OX + edge[2] or y1 > OY + edge[3]: return False
    if hit(lbox, (OX + keepout[0], OY + keepout[1], OX + keepout[2], OY + keepout[3])): return False
    if any(hit(lbox, c) for c in copper): return False
    if any(hit(lbox, g) for ref, g in silk_graphics if not (me[0] == 'ref' and ref == me[1])): return False
    if any(hit(lbox, o) for o in others): return False
    return True
moves = {}
placed_boxes = {}
for kind, txt, obj in labels:
    placed_boxes[(kind, txt)] = box(obj.GetBoundingBox(), 0.1)
for kind, txt, obj in labels:
    me = (kind, txt)
    others = [v for k, v in placed_boxes.items() if k != me]
    bb0 = box(obj.GetBoundingBox(), 0.1)
    if clear(bb0, me, others):
        continue
    best = None
    for r in [i * 0.2 for i in range(1, 31)]:
        for k in range(0, 360, 15):
            dx, dy = r * math.cos(math.radians(k)), r * math.sin(math.radians(k))
            nb = (bb0[0] + dx, bb0[1] + dy, bb0[2] + dx, bb0[3] + dy)
            if clear(nb, me, others):
                best = (dx, dy); break
        if best: break
    pos = obj.GetPosition()
    if best:
        nx, ny = MM(pos.x) + best[0], MM(pos.y) + best[1]
        moves[f'{kind}:{txt}'] = dict(old=[round(MM(pos.x), 3), round(MM(pos.y), 3)], new=[round(nx, 2), round(ny, 2)], shift=round(math.hypot(*best), 2))
        placed_boxes[me] = (bb0[0] + best[0], bb0[1] + best[1], bb0[2] + best[0], bb0[3] + best[1])
    else:
        moves[f'{kind}:{txt}'] = dict(old=[round(MM(pos.x), 3), round(MM(pos.y), 3)], new=None)
json.dump(moves, open('/home/claude/route/silk_moves.json', 'w'), indent=1)
for k, v in moves.items(): print(k, v)
