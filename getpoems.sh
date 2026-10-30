#!/usr/bin/env bash
set -euo pipefail

URL="https://ftp.ripe.net/ripe/dbase/split/ripe.db.poetic-form.gz"
WHOIS_HOST="whois.ripe.net"
OUTDIR="${HOME}/ripe-poetry/poems"
STAMP="$(date +%Y%m%d)"

usage() {
    cat <<EOF
getpoems.sh - download all RIPE poem objects

Usage:
  getpoems.sh [-o DIR] [-h]

Options:
  -o DIR   Output directory (default: ${OUTDIR})
  -h       Show this help
EOF
}

while getopts ":o:h" opt; do
  case "$opt" in
    o) OUTDIR="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) echo "ERROR: -$OPTARG needs a directory" >&2; usage >&2; exit 1 ;;
    *) echo "ERROR: unknown option -$OPTARG" >&2; usage >&2; exit 1 ;;
  esac
done
shift $((OPTIND - 1))

tmpdir="$(mktemp -d)"
cleanup() { rm -rf "$tmpdir"; }

trap cleanup EXIT

forms_gz="$tmpdir/ripe.db.poetic-form.gz"
forms_txt="$tmpdir/ripe.db.poetic-form"
forms_list="$tmpdir/forms.unique"

# 1) Get current poetic forms
curl -fsSL "$URL" -o "$forms_gz"
gzip -dc "$forms_gz" > "$forms_txt"

#echo "got: $tmpdir/"
#ls -la $tmpdir

# 2) Extract unique poetic-form keys (first token after "poetic-form:")
awk -F':' '
  BEGIN { OFS=":" }
  $1 ~ /^[[:space:]]*poetic-form[[:space:]]*$/ {
    v=$2
    sub(/^[[:space:]]+/, "", v)
    sub(/[[:space:]]+$/, "", v)
    if (v != "") print v
  }
' "$forms_txt" | sort -u > "$forms_list"

# 3) For each form, inverse whois query, save per-form file
mkdir -p "$OUTDIR"
while IFS= read -r form; do

  safe_form="$form"
  safe_form="${safe_form//\//_}"
  safe_form="${safe_form// /_}"

  outfile="$OUTDIR/poems-$safe_form.txt"
  whois -h "$WHOIS_HOST" --no-referenced -i form "$form" -T poem > "$outfile"
done < "$forms_list"

# Merge all per-form files into one date-stamped file
merged="$OUTDIR/ripe.db.poem.$STAMP"
cat "$OUTDIR"/poems-*.txt > "$merged"

echo "Wrote per-form files to: $OUTDIR/poems-*.txt"
echo "Wrote merged file to:     $merged"

