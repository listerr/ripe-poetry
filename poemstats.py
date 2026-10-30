#!/usr/bin/env python3
"""
ripe_poem_stats.py

Parse a RIPE DB dump / concatenated whois output containing poem: objects and
produce summary tables.

Examples:
  # Year -> count (auto range from data)
  ./ripe_poem_stats.py years poems.txt

  # Year -> count (explicit range, include missing years)
  ./ripe_poem_stats.py years poems.txt --start 2003 --end 2026

  # Count by author (all)
  ./ripe_poem_stats.py authors poems.txt

  # Count by author (top 10)
  ./ripe_poem_stats.py authors poems.txt --top 10

  # Count by author excluding missing author
  ./ripe_poem_stats.py authors poems.txt --exclude-no-author

  # Count by author including missing author bucket
  ./ripe_poem_stats.py authors poems.txt --include-no-author
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Poem:
    name: str
    created: str
    author: Optional[str]


RE_POEM = re.compile(r"^poem:\s+(\S+)\s*$", re.IGNORECASE)
RE_CREATED = re.compile(r"^created:\s+(\S+)\s*$", re.IGNORECASE)
#RE_AUTHOR = re.compile(r"^author:\s+(\S+)\s*$", re.IGNORECASE)
RE_AUTHOR = re.compile(r"^author:\s*([^\s#]+)", re.IGNORECASE) # trailing comments
# RE_PERSON = re.compile(r"^person:\s+", re.IGNORECASE)  # to avoid parsing person objects


def parse_year(created: str) -> int:
    # Expect ISO-8601-ish: 2026-02-11T19:09:12Z
    m = re.match(r"^(\d{4})-", created)
    if not m:
        raise ValueError(f"Could not parse year from created={created!r}")
    return int(m.group(1))


def iter_poems_from_file(path: str) -> Iterable[Poem]:
    """
    Streaming parser.
    We treat a "poem object" as starting at 'poem:' and ending when we hit:
      - a blank line followed by a non-indented key of a new object, or
      - another 'poem:' line, or  EOF
    Start collecting at poem: until we hit an empty line AND we are not inside
    continued lines. RIPE dumps usually separate objects with blank lines.
    We also stop if we see 'person:' while not in poem collection.
    """

    current_name: Optional[str] = None
    current_created: Optional[str] = None
    current_author: Optional[str] = None
    in_poem = False

    def flush() -> Optional[Poem]:
        nonlocal current_name, current_created, current_author, in_poem
        if not in_poem:
            return None
        # Only accept if we have poem name and created. Author may be absent.
        if current_name and current_created:
            p = Poem(name=current_name, created=current_created, author=current_author)
        else:
            p = None
        current_name = None
        current_created = None
        current_author = None
        in_poem = False
        return p

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")

            m = RE_POEM.match(line)
            if m:
                # new poem starts; flush previous
                prev = flush()
                if prev:
                    yield prev
                in_poem = True
                current_name = m.group(1)
                current_created = None
                current_author = None
                continue

            if not in_poem:
                # Ignore other object types
                continue

            m = RE_CREATED.match(line)
            if m:
                current_created = m.group(1)
                continue

            m = RE_AUTHOR.match(line)
            if m:
                current_author = m.group(1)
                continue

            # Object boundary heuristic: blank line ends current poem object
            if line.strip() == "":
                p = flush()
                if p:
                    yield p
                continue

        # EOF
        p = flush()
        if p:
            yield p



def print_table_multi(headers: List[str], rows: List[List[str]], totals: bool = False) -> None:
    if not rows:
        print("No data.")
        return

    ncol = len(headers)
    widths = [len(h) for h in headers]
    for r in rows:
        for i in range(ncol):
            widths[i] = max(widths[i], len(r[i]))

    # Heuristic: right-align numeric columns (all digits)
    def is_num(s: str) -> bool:
        return s.isdigit()

    # header
    header_line = "  ".join(
        headers[i].ljust(widths[i]) for i in range(ncol)
    )
    sep_line = "  ".join("-" * widths[i] for i in range(ncol))
    print(header_line)
    print(sep_line)

    # rows
    for idx, r in enumerate(rows):
        if totals and idx == len(rows) - 1:
            print(sep_line)

        out = []
        for i in range(ncol):
            if is_num(r[i]):
                out.append(r[i].rjust(widths[i]))
            else:
                out.append(r[i].ljust(widths[i]))
        print("  ".join(out))


def cmd_years(args: argparse.Namespace) -> int:
    poems = list(iter_poems_from_file(args.file))
    if not poems:
        print("No poem objects found.", file=sys.stderr)
        return 2

    years_all = [parse_year(p.created) for p in poems]
    min_y = min(years_all)
    max_y = max(years_all)

    start = args.start if args.start is not None else min_y
    end = args.end if args.end is not None else max_y
    if start > end:
        print("Start year must be <= end year.", file=sys.stderr)
        return 2

    # year -> poem count
    year_counts: Dict[int, int] = {}
    # year -> author -> count
    year_author_counts: Dict[int, Dict[str, int]] = {}
    # global unique authors across the filtered range
    global_authors: set[str] = set()

    for p in poems:
        y = parse_year(p.created)
        if not (start <= y <= end):
            continue

        year_counts[y] = year_counts.get(y, 0) + 1

        a = p.author if (p.author and p.author.strip()) else "(no author)"
        year_author_counts.setdefault(y, {})
        year_author_counts[y][a] = year_author_counts[y].get(a, 0) + 1
        global_authors.add(a)

    want_top = args.authors_max is not None and args.authors_max > 0

    headers = ["Year", "Poems", "Authors"]
    if want_top:
        headers.append("Top Authors")

    rows: List[List[str]] = []

    for y in range(start, end + 1):
        poems_n = year_counts.get(y, 0)
        author_map = year_author_counts.get(y, {})
        uniq_authors_n = len(author_map)

        row = [str(y), str(poems_n), str(uniq_authors_n)]

        if want_top:
            authors_max = args.authors_max
            assert authors_max is not None
            ordered = sorted(author_map.items(), key=lambda kv: (-kv[1], kv[0].lower()))
            names = [name for name, _cnt in ordered]
            if len(names) > authors_max:
                shown = names[:authors_max]
                more = len(names) - authors_max
                top_str = ", ".join(shown) + f", +{more} more"
            else:
                top_str = ", ".join(names)
            row.append(top_str)

        rows.append(row)

    if args.totals:
        total_years = (end - start + 1)
        total_poems = sum(year_counts.get(y, 0) for y in range(start, end + 1))
        total_unique_authors = len(global_authors)

        total_row = [str(total_years), str(total_poems), str(total_unique_authors)]
        if want_top:
            total_row.append("")
        rows.append(total_row)

    print_table_multi(headers, rows, totals=args.totals)
    return 0



def cmd_authors(args: argparse.Namespace) -> int:
    poems = list(iter_poems_from_file(args.file))
    if not poems:
        print("No poem objects found.", file=sys.stderr)
        return 2

    include_no = args.include_no_author
    exclude_no = args.exclude_no_author
    if include_no and exclude_no:
        print("Choose only one of --include-no-author or --exclude-no-author.", file=sys.stderr)
        return 2

    # Default: exclude missing unless explicitly included
    if not include_no and not exclude_no:
        exclude_no = True

    counts: Dict[str, int] = {}
    for p in poems:
        a = p.author
        if a is None or a == "":
            if exclude_no:
                continue
            a = "(no author)"
        counts[a] = counts.get(a, 0) + 1

    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    grand_total_poems = sum(counts.values())
    grand_total_authors = len(counts)

    if args.top is not None:
        if args.top < 1:
            print("--top must be >= 1", file=sys.stderr)
            return 2
        items = items[: args.top]

    rows: List[List[str]] = [[a, str(c)] for a, c in items]

    if args.totals:
        # Totals row shows overall unique authors + overall poems (not just top-N)
        rows.append([str(grand_total_authors), str(grand_total_poems)])

    print_table_multi(["Author", "Poems"], rows, totals=args.totals)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ripe_poem_stats.py",
        description="Summarise RIPE DB poem objects from a dump / whois output file.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_years = sub.add_parser("years", help="Table of Year -> count of poems (includes missing years in range).")
    p_years.add_argument("file", help="Input text file containing poem objects.")
    p_years.add_argument("--start", type=int, default=None, help="Start year (inclusive). Default: min year in data.")
    p_years.add_argument("--end", type=int, default=None, help="End year (inclusive). Default: max year in data.")
    p_years.add_argument("--authors-max", type=int, default=0, help="Add Authors column with up to N deduped, sorted authors per year. Missing authors become '(no author)'.")
    p_years.add_argument("--totals", action="store_true", help="Add a totals row at the bottom.")
    p_years.set_defaults(func=cmd_years)

    p_auth = sub.add_parser("authors", help="Table of count of poems by author.")
    p_auth.add_argument("file", help="Input text file containing poem objects.")
    p_auth.add_argument("--include-no-author", action="store_true", help="Include poems with no author as '(no author)'.")
    p_auth.add_argument("--exclude-no-author", action="store_true", help="Exclude poems with no author.")
    p_auth.add_argument("--top", type=int, default=None, help="Show top N authors. Default: show all.")
    p_auth.add_argument("--totals", action="store_true", help="Add totals row (unique authors, poems)")
    p_auth.set_defaults(func=cmd_authors)

    return p


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
