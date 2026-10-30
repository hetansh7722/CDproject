#!/usr/bin/env python3
"""Symbol Table Generator - Compiler Design project.

Usage:
    python main.py samples/sample_valid.c
    python main.py samples/sample_errors.c --tokens
    python main.py samples/sample_valid.c --json table.json
    python main.py samples/sample_valid.py            # language guessed from .py
    python main.py snippet.txt --lang python          # or chosen explicitly
"""
import argparse
import os
import sys

from symtab import analyze, LANGUAGES
from symtab import report


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a symbol table from a C or Python source file.")
    ap.add_argument("source", help="path to the source file")
    ap.add_argument("--lang", choices=LANGUAGES, help="input language (default: guessed from the file extension, else c)")
    ap.add_argument("--tokens", action="store_true", help="also print the token stream from the lexer")
    ap.add_argument("--json", metavar="FILE", help="also export the symbol table as JSON")
    args = ap.parse_args()

    try:
        with open(args.source, encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"cannot read {args.source}: {e}", file=sys.stderr)
        return 2

    lang = args.lang or ("python" if os.path.splitext(args.source)[1].lower() in (".py", ".pyw") else "c")
    result = analyze(source, lang)

    if args.tokens:
        print("=== TOKENS ===")
        print(report.token_table(result.tokens))
        print()
    print("=== SCOPE TREE ===")
    print(report.scope_tree(result.table))
    print()
    print("=== SYMBOL TABLES (one per scope) ===")
    print(report.symbol_tables(result.table))
    print("=== DIAGNOSTICS ===")
    print(report.diagnostics_text(result.diagnostics))
    print()
    n_sym = sum(len(s.symbols) for s in result.table.all_scopes)
    print(f"{len(result.table.all_scopes)} scope(s), {n_sym} symbol(s), "
          f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(report.to_json(result))
        print(f"JSON written to {args.json}")

    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
