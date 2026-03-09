"""Compile Lark parse trees to Python bytecode via ast.Expression.

Security: AST node whitelist enforced before compile(). Only these nodes
are permitted: BinOp, UnaryOp, Call, Name, Constant, Compare, IfExp.
No Attribute, Subscript, or other nodes that enable sandbox escape.
"""
from __future__ import annotations

import ast
import math
from typing import Any

from lark import Token, Tree

from idleframework.dsl.parser import parse_formula as _parse

MAX_DEPTH = 50
MAX_EXPONENT_VALUE = 1e6  # Prevent astronomical exponents (DoS protection)

# Whitelisted AST node types
_ALLOWED_NODES = frozenset({
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name,
    ast.Constant, ast.Compare, ast.IfExp, ast.Load,
    # Operator nodes
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.USub,
    ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq,
})

def _safe_pow(base: float, exp: float) -> float:
    """Exponentiation with DoS protection against huge exponents."""
    if isinstance(exp, (int, float)) and abs(exp) > MAX_EXPONENT_VALUE:
        raise ValueError(f"Exponent {exp} exceeds safe limit ({MAX_EXPONENT_VALUE})")
    return base ** exp


# Safe builtins for evaluation
_SAFE_BUILTINS: dict[str, Any] = {
    "_safe_pow": _safe_pow,
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "log": math.log,
    "log10": math.log10,
    "ln": math.log,
    "abs": abs,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
    "clamp": lambda val, lo, hi: max(lo, min(val, hi)),
    "round": round,
    "sum": lambda *args: sum(args) if args else 0,
    "prod": lambda *args: math.prod(args) if args else 1,
    "True": True,
    "False": False,
}


class CompiledFormula:
    """A compiled formula ready for repeated evaluation."""

    __slots__ = ("_code", "_source")

    def __init__(self, code: Any, source: str):
        self._code = code
        self._source = source

    @property
    def source(self) -> str:
        return self._source


def compile_formula(text: str) -> CompiledFormula:
    """Parse and compile a formula string to Python bytecode."""
    tree = _parse(text)
    ast_node = _tree_to_ast(tree, depth=0)
    expr = ast.Expression(body=ast_node)
    ast.fix_missing_locations(expr)
    _validate_whitelist(expr)
    code = compile(expr, f"<formula: {text[:50]}>", "eval")
    return CompiledFormula(code, text)


def evaluate_formula(formula: CompiledFormula, variables: dict[str, float] | None = None) -> float:
    """Evaluate a compiled formula with given variable bindings."""
    ns = dict(_SAFE_BUILTINS)
    if variables:
        conflicts = set(variables) & set(_SAFE_BUILTINS)
        if conflicts:
            raise ValueError(f"Variable names conflict with builtins: {conflicts}")
        ns.update(variables)
    return eval(formula._code, {"__builtins__": {}}, ns)


def _validate_whitelist(node: ast.AST) -> None:
    """Verify all AST nodes are in the whitelist. Raises ValueError if not."""
    for child in ast.walk(node):
        if type(child) not in _ALLOWED_NODES:
            raise ValueError(
                f"Disallowed AST node: {type(child).__name__}. "
                f"Only {sorted(n.__name__ for n in _ALLOWED_NODES)} are permitted."
            )


def _tree_to_ast(tree: Tree | Token, depth: int) -> ast.expr:
    """Convert Lark parse tree to Python AST."""
    if depth > MAX_DEPTH:
        raise ValueError(f"Formula exceeds maximum depth of {MAX_DEPTH}")

    if isinstance(tree, Token):
        if tree.type == "NUMBER":
            return ast.Constant(value=float(tree))
        if tree.type == "NAME":
            return ast.Name(id=str(tree), ctx=ast.Load())
        raise ValueError(f"Unexpected token: {tree}")

    d = depth + 1

    if tree.data == "start":
        return _tree_to_ast(tree.children[0], d)

    if tree.data == "number":
        return ast.Constant(value=float(tree.children[0]))

    if tree.data == "variable":
        name = str(tree.children[0])
        if name.startswith("__"):
            raise ValueError(f"Dunder names forbidden: {name}")
        return ast.Name(id=name, ctx=ast.Load())

    if tree.data == "neg":
        return ast.UnaryOp(op=ast.USub(), operand=_tree_to_ast(tree.children[0], d))

    # Power operator — rewritten to _safe_pow() call for DoS protection
    if tree.data == "pow":
        left = _tree_to_ast(tree.children[0], d)
        right = _tree_to_ast(tree.children[1], d)
        return ast.Call(
            func=ast.Name(id="_safe_pow", ctx=ast.Load()),
            args=[left, right],
            keywords=[],
        )

    # Binary operators
    _binops = {
        "add": ast.Add, "sub": ast.Sub, "mul": ast.Mult,
        "div": ast.Div, "mod": ast.Mod,
    }
    if tree.data in _binops:
        return ast.BinOp(
            left=_tree_to_ast(tree.children[0], d),
            op=_binops[tree.data](),
            right=_tree_to_ast(tree.children[1], d),
        )

    # Comparison
    if tree.data == "comparison":
        left = _tree_to_ast(tree.children[0], d)
        op_str = str(tree.children[1])
        right = _tree_to_ast(tree.children[2], d)
        ops = {
            ">": ast.Gt, ">=": ast.GtE, "<": ast.Lt, "<=": ast.LtE,
            "==": ast.Eq, "!=": ast.NotEq,
        }
        return ast.Compare(left=left, ops=[ops[op_str]()], comparators=[right])

    # Function calls
    if tree.data == "func_call":
        func_name = str(tree.children[0])
        if func_name.startswith("__"):
            raise ValueError(f"Dunder function names forbidden: {func_name}")
        if len(tree.children) > 1:
            args_tree = tree.children[1]
            args = [_tree_to_ast(c, d) for c in args_tree.children]
        else:
            args = []

        # Special handling for if() and piecewise()
        if func_name == "if" and len(args) == 3:
            return ast.IfExp(test=args[0], body=args[1], orelse=args[2])

        if func_name == "piecewise" and len(args) >= 3:
            # Build nested IfExp: piecewise(c1,v1,c2,v2,...,default)
            *pairs, default = args
            if len(pairs) % 2 != 0:
                raise ValueError("piecewise requires pairs of (condition, value) + default")
            result = default
            for i in range(len(pairs) - 2, -1, -2):
                result = ast.IfExp(test=pairs[i], body=pairs[i + 1], orelse=result)
            return result

        return ast.Call(
            func=ast.Name(id=func_name, ctx=ast.Load()),
            args=args,
            keywords=[],
        )

    # Fallthrough: try to process children
    if len(tree.children) == 1:
        return _tree_to_ast(tree.children[0], d)

    raise ValueError(f"Unhandled tree node: {tree.data}")
