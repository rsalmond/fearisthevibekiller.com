#!/bin/bash

set -e

./scripts/builder.py future > index.qmd
./scripts/builder.py past > past.qmd
quarto render
git checkout docs/CNAME
