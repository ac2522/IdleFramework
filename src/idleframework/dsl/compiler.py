"""Compile Formula DSL to Python bytecode with AST whitelist security."""

from __future__ import annotations

import ast
import math
from typing import Any

from idleframework.bigfloat import BigFloat
from idleframework.dsl.parser import parse_formula as _parse

# Maximum tree-to-AST recursion depth
_MAX_DEPTH = 50

# AST node whitelist — only these node types are permitted in compiled formulas
_ALLOWED_AST_NODES = frozenset(
    {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.Compare,
        ast.IfExp,
        ast.Load,
        # Operators
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.USub,
        # Comparisons
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.Eq,
        ast.NotEq,
    }
)


def _to_float(x: Any) -> float:
    """Coerce BigFloat to float for math functions, pass through plain numbers."""
    return float(x) if isinstance(x, BigFloat) else x


def _bf_sqrt(x: Any) -> Any:
    """BigFloat-aware sqrt: uses log10 decomposition to avoid float overflow."""
    if isinstance(x, BigFloat):
        # sqrt(m * 10^e) = sqrt(m) * 10^(e/2)
        # For odd exponents: sqrt(m * 10) * 10^((e-1)/2)
        if x.exponent % 2 == 0:
            return BigFloat.from_components(math.sqrt(x.mantissa), x.exponent // 2)
        else:
            return BigFloat.from_components(math.sqrt(x.mantissa * 10.0), (x.exponent - 1) // 2)
    return math.sqrt(x)


def _bf_log10(x: Any) -> float:
    """BigFloat-aware log10: uses BigFloat.log10() directly."""
    if isinstance(x, BigFloat):
        return x.log10()
    return math.log10(x)


def _bf_log(x: Any) -> float:
    """BigFloat-aware natural log: log(m * 10^e) = ln(m) + e * ln(10)."""
    if isinstance(x, BigFloat):
        return math.log(x.mantissa) + x.exponent * math.log(10)
    return math.log(x)


# Safe builtins exposed to formulas
_SAFE_BUILTINS: dict[str, Any] = {
    "sqrt": _bf_sqrt,
    "cbrt": lambda x: x ** (1 / 3) if x >= 0 else -((-x) ** (1 / 3)),
    "log": _bf_log,
    "log10": _bf_log10,
    "ln": _bf_log,
    "abs": abs,
    "min": min,
    "max": max,
    "floor": lambda x: math.floor(_to_float(x)),
    "ceil": lambda x: math.ceil(_to_float(x)),
    "clamp": lambda x, lo, hi: max(lo, min(x, hi)),
    "round": lambda x, *args: round(_to_float(x), *args),
    "sum": lambda *args: sum(args),
    "prod": lambda *args: math.prod(args),
}

# Comparison operator mapping
_COMP_OPS = {
    ">": ast.Gt,
    ">=": ast.GtE,
    "<": ast.Lt,
    "<=": ast.LtE,
    "==": ast.Eq,
    "!=": ast.NotEq,
}


class CompiledFormula:
    """A compiled formula ready for evaluation."""

    __slots__ = ("code", "source")

    def __init__(self, code: Any, source: str) -> None:
        self.code = code
        self.source = source


def _validate_whitelist(node: ast.AST) -> None:
    """Walk AST and reject any node type not in the whitelist."""
    if type(node) not in _ALLOWED_AST_NODES:
        raise ValueError(
            f"Disallowed AST node: {type(node).__name__}. Only whitelisted nodes are permitted."
        )
    for child in ast.iter_child_nodes(node):
        _validate_whitelist(child)


def _tree_to_ast(tree, depth: int = 0) -> ast.expr:
    """Convert a Lark parse tree to a Python AST expression node."""
    if depth > _MAX_DEPTH:
        raise ValueError(f"Depth limit ({_MAX_DEPTH}) exceeded — formula too deeply nested")

    # Terminal tokens (when ?-rules inline the value)
    from lark import Token, Tree

    if isinstance(tree, Token):
        if tree.type == "NUMBER":
            value = float(tree) if ("." in tree or "e" in tree.lower()) else int(tree)
            return ast.Constant(value=value)
        if tree.type == "NAME":
            name = str(tree)
            if name.startswith("__") or name.endswith("__"):
                raise ValueError(f"Dunder names are forbidden: {name}")
            return ast.Name(id=name, ctx=ast.Load())
        raise ValueError(f"Unexpected token type: {tree.type}")

    if not isinstance(tree, Tree):
        raise ValueError(f"Unexpected node: {tree!r}")

    rule = tree.data

    if rule == "number":
        return _tree_to_ast(tree.children[0], depth + 1)

    if rule == "var":
        token = tree.children[0]
        name = str(token)
        if name.startswith("__") or name.endswith("__"):
            raise ValueError(f"Dunder names are forbidden: {name}")
        return ast.Name(id=name, ctx=ast.Load())

    # Binary operators
    _BIN_OPS = {
        "add": ast.Add,
        "sub": ast.Sub,
        "mul": ast.Mult,
        "div": ast.Div,
        "mod": ast.Mod,
        "pow": ast.Pow,
    }
    if rule in _BIN_OPS:
        left = _tree_to_ast(tree.children[0], depth + 1)
        right = _tree_to_ast(tree.children[1], depth + 1)
        return ast.BinOp(left=left, op=_BIN_OPS[rule](), right=right)

    # Unary negation
    if rule == "neg":
        operand = _tree_to_ast(tree.children[0], depth + 1)
        return ast.UnaryOp(op=ast.USub(), operand=operand)

    # Comparisons
    if rule == "comparison":
        left = _tree_to_ast(tree.children[0], depth + 1)
        op_token = str(tree.children[1])
        right = _tree_to_ast(tree.children[2], depth + 1)
        op_cls = _COMP_OPS[op_token]
        return ast.Compare(left=left, ops=[op_cls()], comparators=[right])

    # Function calls
    if rule == "func_call":
        func_name = str(tree.children[0])
        if func_name.startswith("__") or func_name.endswith("__"):
            raise ValueError(f"Dunder names are forbidden: {func_name}")

        args_tree = tree.children[1]  # arguments node
        args = [_tree_to_ast(child, depth + 1) for child in args_tree.children]

        # Special handling for if() -> ast.IfExp
        if func_name == "if":
            if len(args) != 3:
                raise ValueError("if() requires exactly 3 arguments: condition, then, else")
            return ast.IfExp(test=args[0], body=args[1], orelse=args[2])

        # Special handling for piecewise() -> nested IfExp
        if func_name == "piecewise":
            if len(args) < 3 or len(args) % 2 == 0:
                raise ValueError(
                    "piecewise() requires odd number of args >= 3: "
                    "cond1, val1, cond2, val2, ..., default"
                )
            return _build_piecewise(args)

        # Regular function call
        return ast.Call(
            func=ast.Name(id=func_name, ctx=ast.Load()),
            args=args,
            keywords=[],
        )

    # Parenthesized expression — counts toward nesting depth
    if rule == "paren":
        return _tree_to_ast(tree.children[0], depth + 1)

    # arguments node — should not be reached directly
    if rule == "arguments":
        raise ValueError("arguments node should not be converted directly")

    raise ValueError(f"Unhandled rule: {rule}")


def _build_piecewise(args: list[ast.expr]) -> ast.IfExp:
    """Build nested IfExp from piecewise arguments."""
    # Base case: last arg is the default
    if len(args) == 1:
        return args[0]
    # Recursive: if(cond, val, piecewise(rest...))
    cond = args[0]
    val = args[1]
    rest = _build_piecewise(args[2:])
    return ast.IfExp(test=cond, body=val, orelse=rest)


def compile_formula(text: str) -> CompiledFormula:
    """Parse, compile, and validate a formula string.

    Returns a CompiledFormula with a compiled code object ready for eval().
    """
    # Parse with Lark
    tree = _parse(text)

    # Convert Lark tree to Python AST
    expr_node = _tree_to_ast(tree, depth=0)

    # Wrap in ast.Expression for compilation
    module = ast.Expression(body=expr_node)
    ast.fix_missing_locations(module)

    # Validate AST whitelist
    _validate_whitelist(module)

    # Compile to bytecode
    code = compile(module, f"<formula: {text}>", "eval")

    return CompiledFormula(code=code, source=text)


def evaluate_formula(
    formula: CompiledFormula,
    variables: dict[str, Any] | None = None,
) -> Any:
    """Evaluate a compiled formula with the given variables.

    Uses restricted builtins — no access to __builtins__, __import__, etc.
    """
    namespace: dict[str, Any] = {"__builtins__": {}}
    namespace.update(_SAFE_BUILTINS)
    if variables:
        for name in variables:
            if name.startswith("__") or name.endswith("__"):
                raise ValueError(f"Dunder names are forbidden: {name}")
        namespace.update(variables)

    return eval(formula.code, namespace)
