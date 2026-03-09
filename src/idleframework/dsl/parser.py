"""Parse formula strings into Lark parse trees."""
from __future__ import annotations

from pathlib import Path
from lark import Lark

_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"
_parser = Lark(
    _GRAMMAR_PATH.read_text(),
    parser="lalr",
    maybe_placeholders=False,
)


def parse_formula(text: str) -> object:
    """Parse a formula string into a Lark parse tree."""
    return _parser.parse(text)
