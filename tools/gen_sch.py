"""Generate the sensor-interface schematic (KiCad 7 format, opens in KiCad 8-10).

Every symbol comes from the official KiCad library. Connections use short wire
stubs ending in a power symbol or a net label, plus direct wires inside small
RC networks. Run check_net.py afterwards to verify the netlist.
"""
import math, uuid, sys, os, json
from sexp import parse, dump, Sym, fmt, q

LIBDIR = '/usr/share/kicad/symbols'
ROOT_UUID = '1fbb866c-442a-426c-89b3-3649b9a188c9'   # keep the user's root sheet uuid
PROJECT = 'kicad bike project'
G = 1.27

def U():
    return str(uuid.uuid4())

# ---------------------------------------------------------------- library
_libcache = {}
def lib_tree(lib):
    if lib not in _libcache:
        _libcache[lib] = parse(open(f'{LIBDIR}/{lib}.kicad_sym').read())[0]
    return _libcache[lib]

def find_sym(lib, name):
    for n in lib_tree(lib):
        if isinstance(n, list) and n and n[0] == 'symbol' and n[1] == name:
            return n
    raise KeyError(f'{lib}:{name}')

def deep_rename(node, old, new):
    if isinstance(node, list):
        if len(node) > 1 and node[0] == 'symbol' and isinstance(node[1], str) and node[1].startswith(old + '_'):
            node[1] = new + node[1][len(old):]
        for c in node:
            deep_rename(c, old, new)

def flat_symbol(lib_id):
    lib, name = lib_id.split(':')
    import copy
    s = copy.deepcopy(find_sym(lib, name))
    ext = [n for n in s if isinstance(n, list) and n and n[0] == 'extends']
    if ext:
        parent_name = ext[0][1]
        parent = copy.deepcopy(find_sym(lib, parent_name))
        child_props = {n[1]: n for n in s if isinstance(n, list) and n and n[0] == 'property'}
        out = [Sym('symbol'), name]
        for n in parent[2:]:
            if isinstance(n, list) and n and n[0] == 'property':
                out.append(child_props.pop(n[1], n))
            else:
                out.append(n)
        # child-only properties go right after the last property
        idx = max(i for i, n in enumerate(out) if isinstance(n, list) and n and n[0] == 'property') + 1
        for p in child_props.values():
            out.insert(idx, p); idx += 1
        deep_rename(out, parent_name, name)
        s = out
    s[1] = lib_id
    return s

def sym_pins(symnode):
    pins = []
    def walk(n):
        if isinstance(n, list) and n:
            if n[0] == 'pin' and len(n) > 3 and isinstance(n[3], list) and n[3][0] == 'at':
                at = n[3]
                name = num = None
                for c in n:
                    if isinstance(c, list) and c and c[0] == 'name': name = c[1]
                    if isinstance(c, list) and c and c[0] == 'number': num = c[1]
                pins.append(dict(etype=str(n[1]), x=float(at[1]), y=float(at[2]), a=float(at[3]), name=name, num=num))
            for c in n:
                walk(c)
    walk(symnode)
    return pins

def sym_props(symnode):
    out = {}
    for n in symnode:
        if isinstance(n, list) and n and n[0] == 'property':
            at = [c for c in n if isinstance(c, list) and c and c[0] == 'at'][0]
            hidden = 'hide' in dump(n)
            out[n[1]] = dict(val=n[2], x=float(at[1]), y=float(at[2]), a=float(at[3]), hide=hidden)
    return out

# ---------------------------------------------------------------- geometry
def rot(dx, dy, r):
    """Rotate a screen-space offset counter-clockwise (visually) by r degrees."""
    t = math.radians(r)
    c, s = round(math.cos(t)), round(math.sin(t))
    return dx * c + dy * s, -dx * s + dy * c

def snap(v):
    return round(round(v / G) * G, 4)

# ---------------------------------------------------------------- schematic state
lib_used = {}
items = []          # text chunks
symbols_out = []
pin_map = {}        # ref -> {pin_num: (x, y, (dx,dy))}
refcount = {'#PWR': 0, '#FLG': 0}

def use_lib(lib_id):
    if lib_id not in lib_used:
        lib_used[lib_id] = flat_symbol(lib_id)
    return lib_used[lib_id]

def eff(size=1.27, justify=None, hide=False):
    s = f'(effects (font (size {fmt(size)} {fmt(size)}))'
    if justify:
        s += f' (justify {justify})'
    if hide:
        s += ' hide'
    return s + ')'

def place(lib_id, ref, value, x, y, r=0, footprint='', fields=None, ref_at=None, val_at=None, mirror=None):
    s = use_lib(lib_id)
    pins = sym_pins(s)
    props = sym_props(s)
    is_power = ref.startswith('#')
    pm = {}
    for p in pins:
        dx, dy = rot(p['x'], -p['y'], r)
        # pin "a" points from connection point toward the body; outward is opposite
        oa = math.radians(p['a'] + 180)
        ox, oy = round(math.cos(oa)), -round(math.sin(oa))
        ox, oy = rot(ox, oy, r)
        pm.setdefault(p['num'], (snap(x + dx), snap(y + dy), (ox, oy), p['etype']))
    pin_map[ref] = pm
    lines = [f'(symbol (lib_id {q(lib_id)}) (at {fmt(x)} {fmt(y)} {r}) (unit 1)',
             f'  (in_bom {"no" if is_power else "yes"}) (on_board {"no" if is_power else "yes"}) (dnp no)',
             f'  (uuid {U()})']
    def prop(name, val, default_xy, given, hide):
        ang = 0
        if given:
            px, py, just = given[:3]
            ang = given[3] if len(given) > 3 else 0
        else:
            ddx, ddy = rot(default_xy[0], -default_xy[1], r)
            px, py, just = x + ddx, y + ddy, None
        lines.append(f'  (property {q(name)} {q(val)} (at {fmt(snap(px))} {fmt(snap(py))} {ang})')
        lines.append(f'    {eff(justify=just, hide=hide)}')
        lines.append('  )')
    pr = props
    prop('Reference', ref, (pr['Reference']['x'], pr['Reference']['y']), ref_at, is_power or pr['Reference']['hide'])
    prop('Value', value, (pr['Value']['x'], pr['Value']['y']), val_at, False if not is_power else pr['Value']['hide'])
    prop('Footprint', footprint, (0, 0), None, True)
    prop('Datasheet', pr.get('Datasheet', {'val': '~'})['val'], (0, 0), None, True)
    for k, v in (fields or {}).items():
        prop(k, v, (0, 0), None, True)
    for num in sorted({p['num'] for p in pins}, key=lambda t: (len(t), t)):
        lines.append(f'  (pin {q(num)} (uuid {U()}))')
    lines.append(f'  (instances (project {q(PROJECT)} (path {q("/" + ROOT_UUID)} (reference {q(ref)}) (unit 1))))')
    lines.append(')')
    symbols_out.append('\n'.join(lines))
    return pm

def wire(x1, y1, x2, y2):
    items.append(f'(wire (pts (xy {fmt(snap(x1))} {fmt(snap(y1))}) (xy {fmt(snap(x2))} {fmt(snap(y2))})) '
                 f'(stroke (width 0) (type default)) (uuid {U()}))')

def junction(x, y):
    items.append(f'(junction (at {fmt(snap(x))} {fmt(snap(y))}) (diameter 0) (color 0 0 0 0) (uuid {U()}))')

def label(name, x, y, direction):
    """Local label whose text runs in screen direction (dx,dy)."""
    ang, just = {(1, 0): (0, 'left bottom'), (-1, 0): (180, 'right bottom'),
                 (0, -1): (90, 'left bottom'), (0, 1): (270, 'right bottom')}[direction]
    items.append(f'(label {q(name)} (at {fmt(snap(x))} {fmt(snap(y))} {ang}) (fields_autoplaced) '
                 f'{eff(justify=just)} (uuid {U()}))')

def no_connect(x, y):
    items.append(f'(no_connect (at {fmt(snap(x))} {fmt(snap(y))}) (uuid {U()}))')

def text(t, x, y, size=1.27):
    items.append(f'(text {q(t)} (at {fmt(x)} {fmt(y)} 0) {eff(size=size, justify="left bottom")} (uuid {U()}))')

def box(x1, y1, x2, y2):
    items.append(f'(rectangle (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
                 f'(stroke (width 0) (type dash)) (fill (type none)) (uuid {U()}))')

POWER = {'GND': 'power:GND', '+3V3': 'power:+3V3', 'VBUS': 'power:VBUS'}

def power_sym(net, x, y, direction):
    """Power symbol whose body points in screen direction."""
    lib_id = POWER[net]
    if net == 'GND':
        r = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[direction]
    else:
        r = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[direction]
    refcount['#PWR'] += 1
    ref = f'#PWR{refcount["#PWR"]:02d}'
    s = use_lib(lib_id)
    vp = sym_props(s)['Value']
    dx, dy = rot(vp['x'], -vp['y'], r)
    place(lib_id, ref, net, x, y, r)

def pwr_flag(x, y, direction):
    r = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[direction]
    refcount['#FLG'] += 1
    place('power:PWR_FLAG', f'#FLG{refcount["#FLG"]:02d}', 'PWR_FLAG', x, y, r)

def conn(ref, pin, net, stub=2.54, bend=None, bend_len=5.08):
    """Stub out of a pin, then a power symbol or a label. Optional 90-degree bend."""
    x, y, (dx, dy), _ = pin_map[ref][pin]
    ex, ey = x + dx * stub, y + dy * stub
    wire(x, y, ex, ey)
    if bend:
        fx, fy = ex + bend[0] * bend_len, ey + bend[1] * bend_len
        wire(ex, ey, fx, fy)
        ex, ey, dx, dy = fx, fy, bend[0], bend[1]
    if net in POWER:
        power_sym(net, ex, ey, (dx, dy))
    else:
        label(net, ex, ey, (dx, dy))

def nc(ref, pin):
    x, y, _, _ = pin_map[ref][pin]
    no_connect(x, y)

def pin_xy(ref, pin):
    x, y, _, _ = pin_map[ref][pin]
    return x, y

# ---------------------------------------------------------------- footprints
FP_R = 'Resistor_SMD:R_0603_1608Metric'
FP_C = 'Capacitor_SMD:C_0603_1608Metric'
FP_C_BULK = 'Capacitor_SMD:C_0805_2012Metric'
FP_SW = 'Button_Switch_SMD:SW_SPST_TL3342'

def R(ref, val, x, y, fields=None):
    return place('Device:R', ref, val, x, y, 0, FP_R, fields,
                 ref_at=(x + 2.54, y - 1.27, 'left'), val_at=(x + 2.54, y + 1.27, 'left'))

def C(ref, val, x, y, fp=FP_C, fields=None):
    return place('Device:C', ref, val, x, y, 0, fp, fields,
                 ref_at=(x + 2.54, y - 1.27, 'left'), val_at=(x + 2.54, y + 1.27, 'left'))

def SW(ref, val, x, y):
    return place('Switch:SW_Push', ref, val, x, y, 0, FP_SW, None,
                 ref_at=(x, y - 3.81, None), val_at=(x, y + 2.54, None))

# ================================================================ BLOCK A: USB-C
box(15.24, 25.4, 124.46, 119.38)
text('USB-C: 5 V input and programming', 17.78, 31.75, 2.0)
place('Connector:USB_C_Receptacle_USB2.0_16P', 'J1', 'USB_C_USB2.0', 40.64, 81.28, 0,
      'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal',
      {'MPN': 'GCT USB4105-GF-A'})
conn('J1', 'A4', 'VBUS')
conn('J1', 'A5', 'CC1')
conn('J1', 'B5', 'CC2')
conn('J1', 'A7', 'USB_DN')
conn('J1', 'B7', 'USB_DN')
conn('J1', 'A6', 'USB_DP')
conn('J1', 'B6', 'USB_DP')
nc('J1', 'A8')
nc('J1', 'B8')
conn('J1', 'A1', 'GND')
conn('J1', 'S1', 'GND')

R('R8', '5.1k', 76.2, 88.9)
conn('R8', '1', 'CC1')
conn('R8', '2', 'GND')
R('R9', '5.1k', 91.44, 88.9)
conn('R9', '1', 'CC2')
conn('R9', '2', 'GND')
text('CC1/CC2 5.1k pull-downs tell a', 66.04, 106.68)
text('USB-C source to turn on 5 V', 66.04, 109.22)

# power flags: VBUS and GND are fed by passive connector pins
power_sym('VBUS', 106.68, 50.8, (0, -1))
wire(106.68, 50.8, 106.68, 55.88)
pwr_flag(106.68, 55.88, (0, 1))
power_sym('GND', 116.84, 55.88, (0, 1))
wire(116.84, 55.88, 116.84, 50.8)
pwr_flag(116.84, 50.8, (0, -1))

# ================================================================ BLOCK B: regulator + LED
box(139.7, 25.4, 279.4, 88.9)
text('3.3 V regulator and power LED', 142.24, 31.75, 2.0)
place('Regulator_Linear:AP7361C-33E', 'U2', 'AP7361C-33E-13', 187.96, 53.34, 0,
      'Package_TO_SOT_SMD:SOT-223-3_TabPin2',
      ref_at=(193.04, 59.69, 'left'), val_at=(193.04, 62.23, 'left'))
conn('U2', '1', 'VBUS', bend=(0, -1))
conn('U2', '2', 'GND')
conn('U2', '3', '+3V3', bend=(0, -1))

C('C1', '4.7uF 10V', 149.86, 55.88, FP_C_BULK)
conn('C1', '1', 'VBUS'); conn('C1', '2', 'GND')
C('C2', '100nF', 165.1, 55.88)
conn('C2', '1', 'VBUS'); conn('C2', '2', 'GND')
C('C3', '10uF 10V', 213.36, 55.88, FP_C_BULK)
conn('C3', '1', '+3V3'); conn('C3', '2', 'GND')

R('R4', '680', 238.76, 50.8)
conn('R4', '1', '+3V3')
place('Device:LED', 'D1', 'LTST-C191KGKT', 238.76, 63.5, 90, 'LED_SMD:LED_0603_1608Metric',
      {'Color': 'Green'}, ref_at=(241.3, 62.23, 'right', 90), val_at=(241.3, 64.77, 'right', 90))
wire(*pin_xy('R4', '2'), *pin_xy('D1', '2'))
conn('D1', '1', 'GND')
text('In: 4.7uF + 100nF  Out: 10uF (>= 2.2uF ceramic per datasheet)', 142.24, 81.28)
text('LED: (3.3 V - 2.0 V) / 680 = 1.9 mA', 226.06, 81.28)

# ================================================================ BLOCK C: ESP32-S3
box(139.7, 99.06, 279.4, 193.04)
text('ESP32-S3-WROOM-1 module', 142.24, 105.41, 2.0)
U1 = place('RF_Module:ESP32-S3-WROOM-1', 'U1', 'ESP32-S3-WROOM-1-N8', 215.9, 152.4, 0,
           'RF_Module:ESP32-S3-WROOM-1')
conn('U1', '2', '+3V3')
conn('U1', '1', 'GND')
conn('U1', '3', 'EN')
conn('U1', '27', 'BOOT')
conn('U1', '39', 'SENSOR_ADC')     # IO1 = ADC1_CH0
conn('U1', '15', 'GPIO3_STRAP')    # IO3 strapping pin
conn('U1', '4', 'BUTTON')          # IO4
conn('U1', '13', 'USB_DN')         # IO19
conn('U1', '14', 'USB_DP')         # IO20
used = {'1', '2', '3', '27', '39', '15', '4', '13', '14', '40', '41'}
for num in U1:
    if num not in used:
        nc('U1', num)

C('C4', '22uF 10V', 251.46, 129.54, FP_C_BULK)
conn('C4', '1', '+3V3'); conn('C4', '2', 'GND')
C('C5', '100nF', 269.24, 129.54)
conn('C5', '1', '+3V3'); conn('C5', '2', 'GND')
text('C4, C5: place at module 3V3 pin', 243.84, 143.51)
text('GPIO45/46: leave open', 233.68, 186.69)
text('(internal pull-downs)', 233.68, 189.23)

# ================================================================ BLOCK D: reset / boot / strap
box(289.56, 25.4, 406.4, 119.38)
text('Reset, boot and strapping', 292.1, 31.75, 2.0)
# EN: R1 pull-up, C6 delay, SW3 reset
R('R1', '10k', 304.8, 48.26)
conn('R1', '1', '+3V3')
nx, ny = 304.8, 58.42
wire(*pin_xy('R1', '2'), nx, ny)
C('C6', '1uF', 304.8, 66.04)
wire(nx, ny, *pin_xy('C6', '1'))
conn('C6', '2', 'GND')
SW('SW3', 'RESET', 325.12, 58.42)
wire(nx, ny, *pin_xy('SW3', '1'))
conn('SW3', '2', 'GND')
junction(nx, ny)
wire(nx, ny, nx - 5.08, ny)
label('EN', nx - 5.08, ny, (-1, 0))
text('EN delay: 10k x 1uF = 10 ms', 292.1, 78.74)

# BOOT: R2 pull-up on GPIO0, SW2 to GND
R('R2', '10k', 304.8, 93.98)
conn('R2', '1', '+3V3')
bx, by = 304.8, 104.14
wire(*pin_xy('R2', '2'), bx, by)
SW('SW2', 'BOOT', 325.12, 104.14)
wire(bx, by, *pin_xy('SW2', '1'))
conn('SW2', '2', 'GND')
wire(bx, by, bx - 5.08, by)
label('BOOT', bx - 5.08, by, (-1, 0))
junction(bx, by)
text('Hold BOOT, tap RESET = download mode', 292.1, 116.84)

# GPIO3 strap: pull-up, must not float
R('R3', '10k', 368.3, 48.26)
conn('R3', '1', '+3V3')
conn('R3', '2', 'GPIO3_STRAP')
text('GPIO3 has no internal pull;', 350.52, 78.74)
text('datasheet says it must not float', 350.52, 81.28)

# ================================================================ BLOCK E: sensor
box(15.24, 129.54, 124.46, 193.04)
text('Analog sensor input (0 to 3.3 V)', 17.78, 135.89, 2.0)
place('Connector_Generic:Conn_01x03', 'J2', 'SENSOR', 45.72, 160.02, 0,
      'Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical',
      None, ref_at=(45.72, 154.94, None), val_at=(45.72, 166.37, None))
conn('J2', '1', '+3V3', bend=(0, -1))
conn('J2', '2', 'SENSOR_IN', stub=7.62)
conn('J2', '3', 'GND', bend=(0, 1))
text('J2 pin 1: 3V3, pin 2: SIG, pin 3: GND', 20.32, 177.8)

R('R5', '10k 1%', 78.74, 154.94)
conn('R5', '1', 'SENSOR_IN')
px, py = 78.74, 162.56
wire(*pin_xy('R5', '2'), px, py)
R('R6', '30k 1%', 78.74, 170.18)
wire(px, py, *pin_xy('R6', '1'))
conn('R6', '2', 'GND')
cx = 93.98
wire(px, py, cx, py)
C('C7', '100nF', cx, 170.18)
wire(cx, py, *pin_xy('C7', '1'))
conn('C7', '2', 'GND')
junction(px, py)
wire(px, py, px - 5.08, py)
label('SENSOR_ADC', px - 5.08, py, (-1, 0))
text('3.3 V x 30k / 40k = 2.475 V (ADC max 3.1 V)', 20.32, 185.42)
text('RC corner: 1 / (2 pi x 7.5k x 100nF) = 212 Hz', 20.32, 187.96)

# ================================================================ BLOCK F: button
box(289.56, 129.54, 406.4, 193.04)
text('User button (active low)', 292.1, 135.89, 2.0)
R('R7', '10k', 304.8, 152.4)
conn('R7', '1', '+3V3')
qx, qy = 304.8, 162.56
wire(*pin_xy('R7', '2'), qx, qy)
C('C8', '100nF', 304.8, 170.18)
wire(qx, qy, *pin_xy('C8', '1'))
conn('C8', '2', 'GND')
SW('SW1', 'USER', 325.12, qy)
wire(qx, qy, *pin_xy('SW1', '1'))
conn('SW1', '2', 'GND')
junction(qx, qy)
wire(qx, qy, qx - 5.08, qy)
label('BUTTON', qx - 5.08, qy, (-1, 0))
text('Debounce: 10k x 100nF = 1 ms', 292.1, 186.69)

# ================================================================ BLOCK G: mounting holes
box(15.24, 203.2, 124.46, 233.68)
text('Mounting holes (M3)', 17.78, 209.55, 2.0)
for i, hx in enumerate([30.48, 50.8, 71.12, 91.44], start=1):
    place('Mechanical:MountingHole', f'H{i}', 'MountingHole', hx, 220.98, 0,
          'MountingHole:MountingHole_3.2mm_M3')

# ================================================================ write
def build():
    out = [f'(kicad_sch (version 20230121) (generator eeschema)',
           f'  (uuid {ROOT_UUID})',
           '  (paper "A3")',
           '  (title_block (title "Basic Sensor Interface PCB") (date "2026-10-09") (rev "A")',
           '    (company "Sea Otter 2027 bike build, EE subteam")',
           '    (comment 1 "ESP32-S3-WROOM-1, USB-C 5 V in, AP7361C 3.3 V LDO"))',
           '  (lib_symbols']
    for lid, node in lib_used.items():
        out.append('    ' + dump(node, 2))
    out.append('  )')
    for it in items:
        out.append('  ' + it)
    for s in symbols_out:
        out.append('  ' + s.replace('\n', '\n  '))
    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append(')')
    return '\n'.join(out) + '\n'

if __name__ == '__main__':
    dest = sys.argv[1]
    open(dest, 'w').write(build())
    json.dump({r: {k: list(v[:2]) for k, v in pm.items()} for r, pm in pin_map.items()},
              open(os.path.join(os.path.dirname(dest), 'pinmap.json'), 'w'), indent=1)
    print('wrote', dest, 'symbols:', len(symbols_out), 'items:', len(items))
