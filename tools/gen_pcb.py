"""Generate the placed (unrouted) board for the sensor-interface PCB.

KiCad 7 pcbnew API. Footprints come from the official KiCad library and are
linked to the schematic symbols by UUID, so "Update PCB from Schematic" in
KiCad 10 recognises them. Coordinates below are board-relative mm
(0,0 = top-left corner of the 60 x 60 mm outline, y down).
"""
import json, sys
import pcbnew

FPDIR = '/usr/share/kicad/footprints'
OX, OY = 100.0, 100.0          # board origin on the KiCad page
W, H = 60.0, 60.0
SHEETFILE = 'kicad bike project.kicad_sch'

sym = json.load(open('/home/claude/gen/symbols_v10.json'))

def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))

board = pcbnew.NewBoard('/tmp/scratch.kicad_pcb')
board.SetCopperLayerCount(2)

# ------------------------------------------------------------------ nets
NETS = {
    'VBUS':  ['J1.A4', 'J1.A9', 'J1.B4', 'J1.B9', 'U2.1', 'C1.1', 'C2.1'],
    'GND':   ['J1.A1', 'J1.A12', 'J1.B1', 'J1.B12', 'J1.SH', 'U2.2', 'C1.2', 'C2.2', 'C3.2', 'C4.2',
              'C5.2', 'C6.2', 'C7.2', 'C8.2', 'R6.2', 'R8.2', 'R9.2', 'D1.1', 'SW1.2', 'SW2.2',
              'SW3.2', 'J2.3', 'U1.1', 'U1.40', 'U1.41'],
    '+3V3':  ['U2.3', 'C3.1', 'C4.1', 'C5.1', 'U1.2', 'R1.1', 'R2.1', 'R3.1', 'R4.1', 'R7.1', 'J2.1'],
    'Net-(D1-A)': ['R4.2', 'D1.2'],
    '/CC1':  ['J1.A5', 'R8.1'],
    '/CC2':  ['J1.B5', 'R9.1'],
    '/USB_DP': ['J1.A6', 'J1.B6', 'U1.14'],
    '/USB_DN': ['J1.A7', 'J1.B7', 'U1.13'],
    '/EN':   ['U1.3', 'R1.2', 'C6.1', 'SW3.1'],
    '/BOOT': ['U1.27', 'R2.2', 'SW2.1'],
    '/GPIO3_STRAP': ['U1.15', 'R3.2'],
    '/SENSOR_IN': ['J2.2', 'R5.1'],
    '/SENSOR_ADC': ['R5.2', 'R6.1', 'C7.1', 'U1.39'],
    '/BUTTON': ['U1.4', 'R7.2', 'C8.1', 'SW1.1'],
}
netobj = {}
for name in NETS:
    n = pcbnew.NETINFO_ITEM(board, name)
    board.Add(n)
    netobj[name] = n
pad_net = {}
for name, nodes in NETS.items():
    for node in nodes:
        pad_net[node] = name

# ------------------------------------------------------------------ outline
def edge_line(x1, y1, x2, y2):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(x1, y1)); s.SetEnd(P(x2, y2))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1))
    board.Add(s)
for a, b in [((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))]:
    edge_line(*a, *b)

# ------------------------------------------------------------------ footprints
LIB = {
    'R': ('Resistor_SMD', 'R_0603_1608Metric'),
    'C': ('Capacitor_SMD', 'C_0603_1608Metric'),
    'CB': ('Capacitor_SMD', 'C_0805_2012Metric'),
}
placed = {}

def add(ref, x, y, rot=0, side='F'):
    lib, name = sym[ref]['footprint'].split(':')
    fp = pcbnew.FootprintLoad(f'{FPDIR}/{lib}.pretty', name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(sym[ref]['value'])
    fp.SetPath(pcbnew.KIID_PATH('/' + sym[ref]['uuid']))
    try:
        fp.SetProperty('Sheetfile', SHEETFILE); fp.SetProperty('Sheetname', '')
    except Exception:
        pass
    board.Add(fp)
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(rot)
    for pad in fp.Pads():
        num = pad.GetNumber()
        if ref == 'J1' and num == 'S1':
            pad.SetNumber('SH')          # KiCad 10 symbol names the shield pin SH
            num = 'SH'
        key = f'{ref}.{num}'
        if key in pad_net:
            pad.SetNet(netobj[pad_net[key]])
    placed[ref] = fp
    return fp

# --- ESP32-S3 module: top edge, antenna flush with the board edge
add('U1', 30.0, 13.05)          # 0.3 mm in from the edge so its silkscreen stays on the board
# --- USB-C: bottom edge, "PCB Edge" mark of the footprint is 3.675 mm below its origin
add('J1', 30.0, H - 3.675)

# --- mounting holes (top pair sits below the antenna keep-out strip)
add('H1', 4.0, 10.0); add('H2', 56.0, 10.0)
add('H3', 4.0, 56.0); add('H4', 56.0, 56.0)

# --- regulator and its caps, lower left, input facing J1
add('U2', 14.0, 46.0, 180)
add('C1', 21.6, 49.6, 90)        # 4.7uF input
add('C2', 21.6, 46.0, 90)        # 100nF input
add('C3', 21.6, 41.8, 90)        # 10uF output
add('R4', 5.0, 44.0, 90)         # LED resistor
add('D1', 5.0, 47.8, 90)         # power LED

# --- USB-C CC pull-downs beside the connector
add('R8', 26.6, 47.0, 90)
add('R9', 33.4, 47.0, 90)

# --- decoupling at module 3V3 (pin 2) and left-side support parts
add('C5', 17.6, 7.6, 0)          # 100nF, closest to pin 2
add('C4', 17.4, 10.2, 0)         # 22uF
add('R1', 17.6, 13.0, 0)         # EN pull-up
add('C6', 17.6, 15.0, 0)         # EN delay
add('R7', 17.6, 18.4, 0)         # button pull-up
add('C8', 17.6, 20.4, 0)         # button debounce
add('SW3', 7.0, 20.0, 90)        # RESET
add('SW1', 7.0, 31.0, 90)        # USER

# --- strap pull-up under the module (GPIO3 = pin 15, bottom row)
add('R3', 23.6, 29.0, 0)

# --- right side: sensor divider near GPIO1 (pin 39), BOOT near GPIO0 (pin 27)
add('R5', 42.6, 9.0, 0)
add('R6', 42.6, 11.2, 0)
add('C7', 42.6, 13.4, 0)
add('J2', 56.0, 20.0, 270)       # sensor connector on the right edge
add('R2', 42.6, 24.0, 0)         # BOOT pull-up
add('SW2', 53.0, 35.0, 90)       # BOOT

# ------------------------------------------------------------------ reference designator placement
def ref_at(ref, x, y, size=0.8, rot=0):
    t = placed[ref].Reference()
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(0.12))
    t.SetPosition(P(x, y))
    t.SetTextAngleDegrees(rot)

for r in ['C5', 'C4', 'R1', 'C6', 'R7', 'C8']:           # left column: labels to the left
    fx = pcbnew.ToMM(placed[r].GetPosition().x) - OX
    fy = pcbnew.ToMM(placed[r].GetPosition().y) - OY
    ref_at(r, fx - 3.0, fy)
for r in ['R5', 'R6', 'C7', 'R2']:                       # right column: labels to the right
    fx = pcbnew.ToMM(placed[r].GetPosition().x) - OX
    fy = pcbnew.ToMM(placed[r].GetPosition().y) - OY
    ref_at(r, fx + 3.0, fy)
ref_at('C1', 19.6, 49.6); ref_at('C2', 19.6, 46.0); ref_at('C3', 19.6, 41.8)
ref_at('R8', 24.9, 47.0, rot=90); ref_at('R9', 35.1, 47.0, rot=90)
ref_at('R3', 23.6, 30.6)
ref_at('R4', 7.2, 44.0); ref_at('D1', 7.2, 47.8)
ref_at('J1', 39.5, 55.0, size=1.0)

# ------------------------------------------------------------------ silkscreen labels
def silk(text, x, y, size=1.0, rot=0, layer=pcbnew.F_SilkS, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text); t.SetPosition(P(x, y)); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    t.SetBold(bold)
    t.SetTextAngleDegrees(rot)
    board.Add(t)

silk('USB 5V', 30.0, 50.4)
silk('SENSOR', 52.5, 15.2)
for i, lab in enumerate(['3V3', 'SIG', 'GND']):
    py = pcbnew.ToMM(placed['J2'].FindPadByNumber(str(i + 1)).GetPosition().y) - OY
    silk(lab, 50.6, py, 0.8)
silk('RESET', 7.0, 14.8)
silk('USER', 7.0, 25.8)
silk('BOOT', 53.0, 29.8)
silk('PWR', 5.0, 50.6)
silk('SENSOR IF  rev A', 46.0, 44.0, 1.0)
silk('Sea Otter 2027 EE', 46.0, 46.0, 1.0)

# ------------------------------------------------------------------ GND pour on the bottom layer
def zone(net, layer, inset=0.5, priority=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(netobj[net])
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetAssignedPriority(priority)
    o = z.Outline()
    o.NewOutline()
    for x, y in [(inset, inset), (W - inset, inset), (W - inset, H - inset), (inset, H - inset)]:
        o.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))
    board.Add(z)
    return z
zone('GND', pcbnew.B_Cu)

if __name__ == '__main__':
    out = sys.argv[1]
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(out)
    print('saved', out, 'footprints:', len(board.GetFootprints()), 'nets:', board.GetNetCount())
