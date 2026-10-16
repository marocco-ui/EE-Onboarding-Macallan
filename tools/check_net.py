"""Compare KiCad's exported netlist to the intended design."""
import sys
from sexp import parse

EXPECTED = {
    'VBUS':  {'J1.A4', 'J1.A9', 'J1.B4', 'J1.B9', 'U2.1', 'C1.1', 'C2.1'},
    'GND':   {'J1.A1', 'J1.A12', 'J1.B1', 'J1.B12', 'J1.S1', 'U2.2', 'C1.2', 'C2.2', 'C3.2', 'C4.2',
              'C5.2', 'C6.2', 'C7.2', 'C8.2', 'R6.2', 'R8.2', 'R9.2', 'D1.1', 'SW1.2', 'SW2.2',
              'SW3.2', 'J2.3', 'U1.1', 'U1.40', 'U1.41'},
    '+3V3':  {'U2.3', 'C3.1', 'C4.1', 'C5.1', 'U1.2', 'R1.1', 'R2.1', 'R3.1', 'R4.1', 'R7.1', 'J2.1'},
    'LED_A': {'R4.2', 'D1.2'},
    'CC1':   {'J1.A5', 'R8.1'},
    'CC2':   {'J1.B5', 'R9.1'},
    'USB_DP': {'J1.A6', 'J1.B6', 'U1.14'},
    'USB_DN': {'J1.A7', 'J1.B7', 'U1.13'},
    'EN':    {'U1.3', 'R1.2', 'C6.1', 'SW3.1'},
    'BOOT':  {'U1.27', 'R2.2', 'SW2.1'},
    'GPIO3_STRAP': {'U1.15', 'R3.2'},
    'SENSOR_IN': {'J2.2', 'R5.1'},
    'SENSOR_ADC': {'R5.2', 'R6.1', 'C7.1', 'U1.39'},
    'BUTTON': {'U1.4', 'R7.2', 'C8.1', 'SW1.1'},
}

tree = parse(open(sys.argv[1]).read())[0]
nets = [n for n in tree if isinstance(n, list) and n[0] == 'nets'][0][1:]
got = {}
for net in nets:
    name = [c for c in net if isinstance(c, list) and c[0] == 'name'][0][1]
    nodes = set()
    for c in net:
        if isinstance(c, list) and c[0] == 'node':
            ref = [d for d in c if isinstance(d, list) and d[0] == 'ref'][0][1]
            pin = [d for d in c if isinstance(d, list) and d[0] == 'pin'][0][1]
            nodes.add(f'{ref}.{pin}')
    got[name.lstrip('/')] = nodes

ok = True
real = {k: v for k, v in got.items() if len(v) > 1}
single = {k: v for k, v in got.items() if len(v) == 1}
for name, want in EXPECTED.items():
    match = [k for k, v in real.items() if v == want]
    if not match:
        ok = False
        print('MISMATCH', name)
        for k, v in got.items():
            if v & want:
                print('   found', k, sorted(v))
    else:
        print('ok  %-12s -> %-30s (%d pins)' % (name, match[0], len(want)))
extra = [k for k, v in real.items() if v not in EXPECTED.values()]
for k in extra:
    ok = False
    print('UNEXPECTED NET', k, sorted(real[k]))
print('single-pin nets (should all be no-connect pins):', len(single))
print(sorted(n for v in single.values() for n in v))
print('RESULT:', 'PASS' if ok else 'FAIL')
