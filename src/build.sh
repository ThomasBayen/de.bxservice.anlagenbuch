#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
set -e
cd "$(dirname "$0")"
mkdir -p .build
DOCS=../docs

pandoc Praesentation_Mitarbeiter.md -t beamer -H _header.tex \
  --resource-path=".:assets:$DOCS" \
  -o "$DOCS/Praesentation_Mitarbeiter.pdf"

pandoc "$DOCS/QuickReference.md" \
  --pdf-engine=pdflatex \
  -V geometry:a4paper,margin=2.5cm \
  -V lang=en-US \
  -V documentclass=article \
  -V fontsize=11pt \
  -V colorlinks=true \
  --toc \
  -o "$DOCS/QuickReference.pdf"

pandoc "$DOCS/QuickReference_de.md" \
  --pdf-engine=pdflatex \
  -V geometry:a4paper,margin=2.5cm \
  -V lang=de-DE \
  -V documentclass=article \
  -V fontsize=11pt \
  -V colorlinks=true \
  --toc \
  -o "$DOCS/QuickReference_de.pdf"

echo "Built:"
echo "  $DOCS/Praesentation_Mitarbeiter.pdf"
echo "  $DOCS/QuickReference.pdf"
echo "  $DOCS/QuickReference_de.pdf"
