"""Deterministic Sandboxed Conditional Expression Evaluator.

Parses and evaluates boolean conditions (e.g., "amount > 100000", "currency == 'USD'")
against payment transaction context using Python's ast module.
Zero use of eval(), exec(), or arbitrary dynamic execution.
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 3.
"""
import ast
import operator
from typing import Dict, Any, Optional, Set


class SecurityError(Exception):
    """Raised when an expression contains forbidden AST nodes or attempts code execution."""
    pass


class ConditionalExpressionEngine:

    """Safe, AST-sandboxed conditional expression engine for PeX evidence rules."""

    _ALLOWED_OPERATORS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
        ast.Not: operator.not_,
    }

    _ALLOWED_NODES = (
        ast.Expression,
        ast.BoolOp,
        ast.Compare,
        ast.UnaryOp,
        ast.Name,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Load,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.In,
        ast.NotIn,
        ast.And,
        ast.Or,
        ast.Not,
    )

    @classmethod
    def evaluate(cls, expression: Optional[str], context: Dict[str, Any]) -> bool:
        """Evaluates an expression string against a context dictionary.

        Args:
            expression: Condition string like 'amount > 100000' or None/empty (which defaults to True).
            context: Dictionary containing transaction variables.

        Returns:
            bool: True if condition is met or expression is None/empty; False otherwise.
        """
        if not expression or not expression.strip():
            return True

        expression = expression.strip()
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid condition expression syntax '{expression}': {e}") from e

        cls._validate_ast(tree)
        return bool(cls._eval_node(tree.body, context))

    @classmethod
    def _validate_ast(cls, node: ast.AST) -> None:
        """Ensures the AST contains only strictly permitted node types."""
        for subnode in ast.walk(node):
            if not isinstance(subnode, cls._ALLOWED_NODES):
                raise SecurityError(
                    f"Forbidden node type '{type(subnode).__name__}' in expression. "
                    f"Only simple comparison, logical, and literal expressions are permitted."
                )

    @classmethod
    def _eval_node(cls, node: ast.AST, context: Dict[str, Any]) -> Any:
        """Recursively evaluates permitted AST nodes against the context."""
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            # Resolve variable from context
            return context.get(node.id, None)

        if isinstance(node, (ast.List, ast.Tuple)):
            return [cls._eval_node(elt, context) for elt in node.elts]

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                operand_val = cls._eval_node(node.operand, context)
                return not operand_val
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for val in node.values:
                    if not cls._eval_node(val, context):
                        return False
                return True
            elif isinstance(node.op, ast.Or):
                for val in node.values:
                    if cls._eval_node(val, context):
                        return True
                return False
            raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")

        if isinstance(node, ast.Compare):
            left_val = cls._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                right_val = cls._eval_node(comparator, context)
                op_type = type(op)
                if op_type not in cls._ALLOWED_OPERATORS:
                    raise ValueError(f"Unsupported comparison operator: {op_type.__name__}")
                
                # Handle None comparisons safely
                if left_val is None or right_val is None:
                    if op_type == ast.Eq:
                        res = (left_val == right_val)
                    elif op_type == ast.NotEq:
                        res = (left_val != right_val)
                    else:
                        return False
                else:
                    try:
                        res = cls._ALLOWED_OPERATORS[op_type](left_val, right_val)
                    except TypeError:
                        return False
                
                if not res:
                    return False
                left_val = right_val
            return True

        raise ValueError(f"Unsupported AST node evaluation: {type(node).__name__}")

    @classmethod
    def extract_variables(cls, expression: Optional[str]) -> Set[str]:
        """Extracts all variable names referenced in the condition expression."""
        if not expression or not expression.strip():
            return set()
        tree = ast.parse(expression.strip(), mode="eval")
        cls._validate_ast(tree)
        return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
