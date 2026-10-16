"""Add locked pre-routes to the base board: USB pair (connector tie copied from vD) and a short +3V3 bottom hop."""
import pcbnew, shutil
shutil.copy('base.kicad_pcb', 'pre.kicad_pcb'); shutil.copy('base.kicad_pro', 'pre.kicad_pro'); shutil.copy('base.kicad_dru', 'pre.kicad_dru')
b = pcbnew.LoadBoard('pre.kicad_pcb')
N = b.GetNetsByName()
for z in b.Zones():
    z.UnFill()
def V(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def trk(net, layer, pts, w):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2))
        t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(layer); t.SetNet(N[net]); t.SetLocked(True); b.Add(t)
def via(net, x, y, d, dr):
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(pcbnew.FromMM(d)); v.SetDrill(pcbnew.FromMM(dr))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(N[net]); v.SetLocked(True); b.Add(v)
F, B = pcbnew.F_Cu, pcbnew.B_Cu
# --- USB D+ : connector tie above the pads (from vD), then up and 45 deg to module pin 14
trk('/USB_DP', F, [(129.75, 152.645), (129.75, 151.962), (129.952, 151.76), (130.489, 151.76), (130.75, 152.021), (130.75, 152.645)], 0.2)
c2 = -13.145
trk('/USB_DP', F, [(129.952, 151.76), (129.952, 129.952 - c2), (121.25, 121.25 - c2), (121.25, 124.3)], 0.2)
# --- USB D- : connector tie just past the pad row (from vD), then up and 45 deg, enters pin 13 from the left
trk('/USB_DN', F, [(129.25, 152.645), (129.25, 153.269), (129.511, 153.53), (130.048, 153.53), (130.25, 153.328), (130.25, 152.645)], 0.2)
c1 = -14.135
trk('/USB_DN', F, [(129.25, 152.645), (129.25, 129.25 - c1), (120.198, 120.198 - c1), (120.198, 123.03), (121.25, 123.03)], 0.2)
# --- +3V3 hop under the USB pair, just below the module
via('+3V3', 118.9, 127.6, 0.8, 0.4)
via('+3V3', 122.78, 127.6, 0.8, 0.4)
trk('+3V3', B, [(118.9, 127.6), (122.78, 127.6)], 0.4)
b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save('pre.kicad_pcb')
print('saved')
