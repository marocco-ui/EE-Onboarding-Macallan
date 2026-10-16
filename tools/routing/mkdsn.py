import re, sys
SRC = 'base.dsn'
def variant(power_w, gnd_w, power_via='Via[0-1]_800:400_um', gnd_via='Via[0-1]_600:300_um'):
    s = open(SRC).read()
    start = s.index('    (class Power')
    end = s.index('\n    )\n', start) + len('\n    )\n')
    new = f'''    (class Power +3V3 VBUS
      (circuit
        (use_via {power_via})
      )
      (rule
        (width {power_w})
        (clearance 200.1)
      )
    )
    (class GNDCLS GND
      (circuit
        (use_via {gnd_via})
      )
      (rule
        (width {gnd_w})
        (clearance 200.1)
      )
    )
'''
    return s[:start] + new + s[end:]
if __name__ == '__main__':
    name, pw, gw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    pv = sys.argv[4] if len(sys.argv) > 4 else 'Via[0-1]_800:400_um'
    open(f'{name}.dsn', 'w').write(variant(pw, gw, pv))
