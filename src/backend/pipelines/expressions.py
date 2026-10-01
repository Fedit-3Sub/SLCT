"""로직 실행기에서 쓰는 식(expression) 평가기.

분기 조건(sequenceFlow 의 conditionExpression)과 노드 입력의 source 값을
평가한다. 사용자가 그린 다이어그램에서 들어오는 문자열이므로 eval 을 쓰지 않고,
파이썬 문법으로 파싱한 뒤 허용한 노드만 직접 계산한다.

식에서 쓸 수 있는 이름
- 실행 입력값과 앞선 노드의 출력값: `기온`, `예측등급`
- 노드 출력 묶음: `Task_1.PM10`, `Task_1["PM2.5"]`
- 이름에 특수문자가 있는 값: `var("PM2.5")`, 없을 때 기본값: `var("관광지", "F-KR-109941-0013")`

Camunda 식(`${...}`)과 JS 연산자(`&&`, `||`, `===`, `true` 등)는 흔히 쓰이므로
파이썬 문법으로 바꿔서 받아준다.
"""

from __future__ import annotations

import ast
import operator
import re
from typing import Any, Callable, Dict, Mapping

MAX_EXPRESSION_LENGTH = 1000


class ExpressionError(ValueError):
    """식을 해석하거나 계산할 수 없을 때."""


_BIN_OPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

_UNARY_OPS: Dict[type, Callable[[Any], Any]] = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_CMP_OPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}

_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "len": len,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
}

# JS 식 표기 → 파이썬 표기. 문자열 안쪽까지 바꾸지 않도록 따옴표 구간은 건너뛴다.
_JS_TOKENS = [
    (re.compile(r"&&"), " and "),
    (re.compile(r"\|\|"), " or "),
    (re.compile(r"===?"), "=="),
    (re.compile(r"!(?!=)"), " not "),
    (re.compile(r"\btrue\b"), "True"),
    (re.compile(r"\bfalse\b"), "False"),
    (re.compile(r"\b(null|undefined)\b"), "None"),
]
_STRING_SPLIT = re.compile(r"""("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')""")


def normalize(source: str) -> str:
    """`${...}` 감싸기와 JS 연산자를 파이썬 식으로 정리한다."""
    text = (source or "").strip()
    wrapped = re.fullmatch(r"[$#]\{(.*)\}", text, flags=re.S)
    if wrapped:
        text = wrapped.group(1).strip()

    parts = _STRING_SPLIT.split(text)
    for index in range(0, len(parts), 2):  # 짝수 번째가 따옴표 밖
        chunk = parts[index]
        # "!==" 가 아래 "===?" 규칙에 걸려 "!==" 로 남지 않도록 먼저 바꾼다.
        chunk = chunk.replace("!==", "!=")
        for pattern, replacement in _JS_TOKENS:
            chunk = pattern.sub(replacement, chunk)
        parts[index] = chunk
    return "".join(parts).strip()


class _Evaluator:
    def __init__(self, names: Mapping[str, Any]):
        self.names = names

    def visit(self, node: ast.AST) -> Any:
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is None:
            raise ExpressionError(f"허용하지 않는 식 요소입니다: {type(node).__name__}")
        return method(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[node.id]
        if node.id not in self.names:
            raise ExpressionError(f"정의되지 않은 값입니다: {node.id}")
        return self.names[node.id]

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        base = self.visit(node.value)
        if isinstance(base, Mapping):
            if node.attr not in base:
                raise ExpressionError(f"값이 없습니다: {node.attr}")
            return base[node.attr]
        # 객체 속성 접근은 막는다(파이썬 내부 속성 노출 방지).
        raise ExpressionError(f"속성 접근은 노드 출력에만 쓸 수 있습니다: {node.attr}")

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        base = self.visit(node.value)
        key = self.visit(node.slice)
        try:
            return base[key]
        except (KeyError, IndexError, TypeError) as exc:
            raise ExpressionError(f"값이 없습니다: {key!r}") from exc

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if isinstance(node.op, ast.And):
            result: Any = True
            for value in node.values:
                result = self.visit(value)
                if not result:
                    return result
            return result
        result = False
        for value in node.values:
            result = self.visit(value)
            if result:
                return result
        return result

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ExpressionError("허용하지 않는 연산자입니다.")
        left, right = self.visit(node.left), self.visit(node.right)
        if not (isinstance(node.op, ast.Add) and isinstance(left, str) and isinstance(right, str)):
            left, right = _as_number(left), _as_number(right)
        try:
            return op(left, right)
        except (TypeError, ZeroDivisionError) as exc:
            raise ExpressionError(str(exc)) from exc

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ExpressionError("허용하지 않는 연산자입니다.")
        operand = self.visit(node.operand)
        if isinstance(node.op, (ast.USub, ast.UAdd)):
            operand = _as_number(operand)
        return op(operand)

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            op = _CMP_OPS.get(type(op_node))
            if op is None:
                raise ExpressionError("허용하지 않는 비교입니다.")
            a, b = _coerce_pair(left, right)
            try:
                if not op(a, b):
                    return False
            except TypeError as exc:
                raise ExpressionError(f"비교할 수 없는 값입니다: {left!r}, {right!r}") from exc
            left = right
        return True

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        return self.visit(node.body) if self.visit(node.test) else self.visit(node.orelse)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name) or node.keywords:
            raise ExpressionError("함수는 이름으로만 호출할 수 있습니다.")
        args = [self.visit(arg) for arg in node.args]
        if node.func.id == "var":
            # var("이름") 또는 var("이름", 기본값). 기본값이 있으면 값이 없어도 오류가 아니다.
            if len(args) not in (1, 2):
                raise ExpressionError("var() 에는 이름과 선택적 기본값을 넘겨야 합니다.")
            if args[0] in self.names and self.names[args[0]] is not None:
                return self.names[args[0]]
            if len(args) == 2:
                return args[1]
            raise ExpressionError(f"정의되지 않은 값입니다: {args[0]}")
        func = _FUNCTIONS.get(node.func.id)
        if func is None:
            raise ExpressionError(f"쓸 수 없는 함수입니다: {node.func.id}")
        try:
            return func(*args)
        except (TypeError, ValueError) as exc:
            raise ExpressionError(str(exc)) from exc

    def visit_List(self, node: ast.List) -> Any:
        return [self.visit(item) for item in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        return tuple(self.visit(item) for item in node.elts)

    def visit_Dict(self, node: ast.Dict) -> Any:
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values) if k is not None}


def _as_number(value: Any) -> Any:
    """숫자 모양 문자열은 숫자로 바꾼다. 외부 API 가 숫자를 문자열로 주는 일이 흔하다."""
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    return value


def _coerce_pair(left: Any, right: Any):
    """한쪽이 숫자면 다른 쪽 숫자 문자열도 숫자로 맞춰 비교한다."""
    if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, str):
        return left, _as_number(right)
    if isinstance(right, (int, float)) and not isinstance(right, bool) and isinstance(left, str):
        return _as_number(left), right
    return left, right


def evaluate(source: str, names: Mapping[str, Any]) -> Any:
    """식을 평가해 값을 돌려준다. 문법 오류나 허용하지 않은 요소는 ExpressionError."""
    text = normalize(source)
    if not text:
        raise ExpressionError("식이 비어 있습니다.")
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise ExpressionError("식이 너무 깁니다.")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"식을 해석할 수 없습니다: {source}") from exc
    return _Evaluator(names).visit(tree)
