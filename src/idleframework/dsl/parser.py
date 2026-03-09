"""Lark-based parser for the Formula DSL."""

from __future__ import annotations

from pathlib import Path

from lark import Lark, Tree

_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"

_parser: Lark | None = None


def _get_parser() -> Lark:
    """Lazily load and cache the Lark parser."""
    global _parser
    if _parser is None:
        _parser = Lark(
            _GRAMMAR_PATH.read_text(),
            parser="lalr",
            maybe_placeholders=False,
        )
    return _parser


def parse_formula(text: str) -> Tree:
    """Parse a formula string into a Lark Tree."""
    return _get_parser().parse(text)
