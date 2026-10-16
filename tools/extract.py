import re, sys, json
def get_symbol(libfile, name):
    txt=open(f'/usr/share/kicad/symbols/{libfile}.kicad_sym').read()
    i=txt.index(f'(symbol "{name}"')
    d=0
    for j in range(i,len(txt)):
        c=txt[j]
        if c=='(': d+=1
        elif c==')':
            d-=1
            if d==0: break
    return txt[i:j+1]
pin_re=re.compile(r'\(pin (\w+) (\w+) \(at ([-\d.]+) ([-\d.]+) (\d+)\) \(length ([\d.]+)\)( hide)?\s*\(name "([^"]*)"[^\n]*\n\s*\(number "([^"]*)"')
def pins(s):
    return [m.groups() for m in pin_re.finditer(s)]
if __name__=='__main__':
    for lib,name in [(a.split(':')[0],a.split(':')[1]) for a in sys.argv[1:]]:
        s=get_symbol(lib,name)
        print('==',lib,name)
        ext=re.search(r'\(extends "([^"]+)"\)',s)
        if ext: print('EXTENDS',ext.group(1))
        fp=re.search(r'\(property "Footprint" "([^"]*)"',s); print('FP',fp.group(1) if fp else None)
        ds=re.search(r'\(property "Datasheet" "([^"]*)"',s); print('DS',ds.group(1) if ds else None)
        for p in pins(s): print(p)
