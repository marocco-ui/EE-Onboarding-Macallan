"""Hide the Description field on every placed symbol (KiCad 9/10 format). Leaves library copies alone."""
import sys
path = sys.argv[1]
raw = open(path, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in raw else '\n'
lines = raw.split(nl)
out, inprop, changed, already = [], False, 0, 0
for ln in lines:
    out.append(ln)
    if ln.startswith('\t\t(property "Description" '):
        inprop = True
        continue
    if inprop:
        if ln == '\t\t\t(hide yes)':
            already += 1; inprop = False
        elif ln == '\t\t\t(do_not_autoplace no)' or ln == '\t\t\t(do_not_autoplace yes)':
            out.append('\t\t\t(hide yes)'); changed += 1; inprop = False
        elif ln.startswith('\t\t)'):
            inprop = False
open(path, 'w', encoding='utf-8', newline='').write(nl.join(out))
print('hidden:', changed, 'already hidden:', already)
