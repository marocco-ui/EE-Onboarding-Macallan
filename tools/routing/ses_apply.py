"""Apply a Specctra .ses (Freerouting output) to a KiCad board via the pcbnew API."""
import re, sys
sys.path.insert(0, '/home/claude/gen')
from sexp import parse
import pcbnew

def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]

def apply_ses(board, ses_path):
    root = parse(open(ses_path).read())[0]
    routes = find(root, 'routes')[0]
    res = find(routes, 'resolution')[0]
    unit = {'um': 1e-3, 'mil': 0.0254, 'mm': 1.0}[str(res[1])] / float(res[2])   # mm per unit
    def P(x, y):
        return pcbnew.VECTOR2I(pcbnew.FromMM(float(x) * unit), pcbnew.FromMM(-float(y) * unit))
    layer_id = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
    nets = board.GetNetsByName()
    n_tr = n_via = 0
    for net in find(find(routes, 'network_out')[0], 'net'):
        name = net[1]
        ni = nets[name] if nets.has_key(name) else None
        for w in find(net, 'wire'):
            path = find(w, 'path')[0]
            lay, width, pts = str(path[1]), float(path[2]) * unit, path[3:]
            xy = [(pts[i], pts[i + 1]) for i in range(0, len(pts) - 1, 2)]
            for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2))
                t.SetWidth(pcbnew.FromMM(width)); t.SetLayer(layer_id[lay])
                if ni: t.SetNet(ni)
                board.Add(t); n_tr += 1
        for v in find(net, 'via'):
            m = re.search(r'_(\d+):(\d+)_um', str(v[1]))
            dia, drill = int(m.group(1)) / 1000.0, int(m.group(2)) / 1000.0
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(P(v[2], v[3]))
            via.SetWidth(pcbnew.FromMM(dia)); via.SetDrill(pcbnew.FromMM(drill))
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            if ni: via.SetNet(ni)
            board.Add(via); n_via += 1
    return n_tr, n_via
