#!/bin/bash
# Convert a Markdown document to PDF via pandoc + wkhtmltopdf, using a
# built-in stylesheet with Japanese (Noto CJK) font support for headings,
# tables, code blocks, and blockquotes. Mermaid fenced code blocks are NOT
# rendered as diagrams -- they appear as plain code text; render them to
# images separately first if diagrams are required in the PDF.
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <input.md> <output.pdf> [--dry-run] [--confirm]"
    echo "example: $BASENAME design.md design.pdf"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

DRY_RUN=false
CONFIRM=false
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --confirm) CONFIRM=true ;;
    --*)
      usage "Unknown option: $arg"
      exit 1
      ;;
    *) ARGS+=("$arg") ;;
  esac
done

if [ "${#ARGS[@]}" -ne 2 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

INPUT_MD="${ARGS[0]}"
OUTPUT_PDF="${ARGS[1]}"

if [ ! -f "$INPUT_MD" ]; then
  echo "$BASENAME: input file not found: $INPUT_MD" >&2
  exit 1
fi

if [ -e "$OUTPUT_PDF" ]; then
  echo "$BASENAME: output already exists, refusing to overwrite: $OUTPUT_PDF" >&2
  exit 1
fi

CSS="$SCRIPT_DIR/markdown_pdf_convert.css"
if [ ! -f "$CSS" ]; then
  echo "$BASENAME: missing stylesheet: $CSS" >&2
  exit 1
fi

echo "$BASENAME: input:  $INPUT_MD" >&2
echo "$BASENAME: output: $OUTPUT_PDF" >&2
echo "$BASENAME: style:  $CSS" >&2

if "$DRY_RUN"; then
  echo "$BASENAME: (dry-run: PDFは生成しません)" >&2
  exit 0
fi

if "$CONFIRM"; then
  read -r -p "上記のとおり変換しますか？ [y/N] " answer
  if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
    echo "$BASENAME: Aborted." >&2
    exit 1
  fi
fi

pandoc "$INPUT_MD" -o "$OUTPUT_PDF" \
  --pdf-engine=wkhtmltopdf \
  --css="$CSS" \
  -V margin-top=15mm -V margin-bottom=15mm -V margin-left=18mm -V margin-right=18mm \
  >&2

echo "$BASENAME: 完了。mermaidブロックは図として描画されず、コードのまま表示されます。図が必要な場合は別途画像化して埋め込んでください。" >&2
echo "$BASENAME: 次にできること: 生成されたPDFを開いて確認する。" >&2
