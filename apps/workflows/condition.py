"""
Condition evaluator for workflow steps.

A condition is a JSON dict:
  {
    "field": "dynamic_data.estimated_cost",   # dotted path
    "operator": ">" | ">=" | "==" | "!=" | "<" | "<=" | "in" | "not_in" | "contains",
    "value": 5000
  }

Or a compound:
  {"all": [cond1, cond2]}
  {"any": [cond1, cond2]}
  {"not": cond1}
"""
import logging

logger = logging.getLogger(__name__)


def _resolve_path(obj, path):
    """Resolve 'dynamic_data.estimated_cost' against a ticket."""
    parts = path.split('.')
    value = obj
    for p in parts:
        if value is None:
            return None
        if isinstance(value, dict):
            value = value.get(p)
        else:
            value = getattr(value, p, None)
    return value


def _apply_operator(left, op, right):
    if op == '==':
        return left == right
    if op == '!=':
        return left != right
    if op == '>':
        return left is not None and left > right
    if op == '>=':
        return left is not None and left >= right
    if op == '<':
        return left is not None and left < right
    if op == '<=':
        return left is not None and left <= right
    if op == 'in':
        return left in (right or [])
    if op == 'not_in':
        return left not in (right or [])
    if op == 'contains':
        return right in (left or '')
    return False


def evaluate(condition, obj):
    """
    Return True/False for a condition dict against `obj` (usually a ticket).
    Empty condition → True (no condition = always apply).
    """
    if not condition:
        return True

    if not isinstance(condition, dict):
        return True

    # Compound conditions
    if 'all' in condition:
        return all(evaluate(c, obj) for c in condition['all'])
    if 'any' in condition:
        return any(evaluate(c, obj) for c in condition['any'])
    if 'not' in condition:
        return not evaluate(condition['not'], obj)

    # Leaf condition
    field = condition.get('field')
    op = condition.get('operator', '==')
    expected = condition.get('value')

    if not field:
        return True

    actual = _resolve_path(obj, field)
    try:
        return _apply_operator(actual, op, expected)
    except Exception as e:
        logger.warning(f"Condition eval error on {field} {op} {expected}: {e}")
        return False