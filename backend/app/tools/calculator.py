import ast
import math
import operator
from collections.abc import Callable
from typing import cast

OPERATIONS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def calculate(expression: str) -> str:
    if not expression or len(expression) > 200:
        raise ValueError("La expresión debe tener entre 1 y 200 caracteres.")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError("La expresión es demasiado compleja.")

    def walk(node: ast.AST, depth: int = 0) -> float:
        if depth > 12:
            raise ValueError("La expresión es demasiado profunda.")
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = float(cast(int | float, node.value))
            if not math.isfinite(value) or abs(value) > 1e12:
                raise ValueError("Número fuera del rango permitido.")
            return value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = walk(node.operand, depth + 1)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATIONS:
            left, right = walk(node.left, depth + 1), walk(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and (abs(right) > 10 or (left == 0 and right < 0)):
                raise ValueError("Exponente fuera del rango permitido.")
            value = OPERATIONS[type(node.op)](left, right)
            if isinstance(value, complex) or not math.isfinite(value) or abs(value) > 1e18:
                raise ValueError("Resultado fuera del rango permitido.")
            return value
        raise ValueError("Solo se admiten números, paréntesis y + - * / // % **.")

    result = walk(tree.body)
    return format(result, ".12g")
