#!/bin/bash
# render.sh board.kicad_pcb outprefix
kicad-cli pcb export pdf --layers "F.Cu,F.Silkscreen,Edge.Cuts,F.Mask" -o $2_top.pdf "$1" >/dev/null 2>&1
kicad-cli pcb export pdf --layers "B.Cu,Edge.Cuts" -o $2_bot.pdf "$1" >/dev/null 2>&1
pdftoppm -png -r 250 -x 935 -y 935 -W 690 -H 690 $2_top.pdf $2_top
pdftoppm -png -r 250 -x 935 -y 935 -W 690 -H 690 $2_bot.pdf $2_bot
