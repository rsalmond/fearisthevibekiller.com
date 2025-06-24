#!/bin/bash

python3 scripts/builder.py future > index.qmd
python3 scripts/builder.py past > past.qmd
quarto render
git checkout docs/CNAME
