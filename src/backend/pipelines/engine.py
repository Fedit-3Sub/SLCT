"""BPMN 서비스 로직 실행기.

저작도구에서 만든 BPMN XML 을 서버에서 해석해 실제로 실행한다.
프런트엔드 토큰 시뮬레이션이 노드마다 요청만 던지고 결과를 버리는 것과 달리,
여기서는 노드 호출 결과를 받아 다음 노드의 입력으로 넘기고 분기 조건을 평가한다.

지원 범위
- 순서 흐름(sequenceFlow)과 조건식, 기본 흐름(default)
- 배타(exclusive)·병렬(parallel)·포괄(inclusive) 게이트웨이의 분기와 합류
- 하위 프로세스(subProcess): 안쪽 흐름을 끝까지 실행한 뒤 바깥으로 이어간다
- 타이머 중간 이벤트(timeDuration): 대기
- 오류 경계 이벤트: 노드 호출이 실패하면 경계 이벤트 쪽 흐름으로 이어간다

병렬 가지는 토큰 대기열로 번갈아 처리한다(동시에 호출하지 않는다).

노드 실행 설정은 확장 요소에서 읽는다.

    <bpmn:extensionElements>
      <pipeline:parameters>
        <pipeline:parameter url="..." method="POST" timeout="30" retry="1" delay="0" />
        <pipeline:input name="기온" source="Task_1.기온" />   <!-- 식으로 값 계산 -->
        <pipeline:input name="지역코드" value="47111" />       <!-- 고정 값 -->
        <pipeline:input name="풍속" />                          <!-- 같은 이름의 값을 자동 연결 -->
        <pipeline:output name="PM10" path="data.PM10" />       <!-- 응답에서 꺼낼 위치 -->
      </pipeline:parameters>
    </bpmn:extensionElements>
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Mapping, Optional, Tuple

from .expressions import ExpressionError, evaluate

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
PIPELINE_NS = "pipeline://"
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"

MAX_XML_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_STEPS = 1000
DEFAULT_MAX_WAIT_SECONDS = 60.0

TASK_TAGS = {
    "task", "serviceTask", "sendTask", "receiveTask", "userTask", "manualTask",
    "scriptTask", "businessRuleTask", "callActivity",
}
GATEWAY_TAGS = {"exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway", "complexGateway"}
EVENT_TAGS = {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent"}
FLOW_NODE_TAGS = TASK_TAGS | GATEWAY_TAGS | EVENT_TAGS | {"subProcess", "transaction", "adHocSubProcess"}
SCOPE_TAGS = {"subProcess", "transaction", "adHocSubProcess"}


class ExecutionError(RuntimeError):
    """실행을 계속할 수 없는 오류."""


class ModelError(ValueError):
    """다이어그램을 해석할 수 없는 오류."""


def _tag(element: ET.Element) -> Tuple[str, str]:
    """(네임스페이스, 로컬 이름)."""
    if element.tag.startswith("{"):
        ns, local = element.tag[1:].split("}", 1)
        return ns, local
    return "", element.tag


def _bpmn(local: str) -> str:
    return f"{{{BPMN_NS}}}{local}"


# ---------------------------------------------------------------------------
# 모델
# ---------------------------------------------------------------------------

@dataclass
class InputSpec:
    name: str
    source: str = ""   # 식
    value: Optional[str] = None  # 고정 값


@dataclass
class OutputSpec:
    name: str
    path: str = ""


@dataclass
class NodeConfig:
    url: str = ""
    method: str = ""
    timeout: float = 30.0
    retry: int = 0
    delay: float = 0.0
    inputs: List[InputSpec] = field(default_factory=list)
    outputs: List[OutputSpec] = field(default_factory=list)


@dataclass
class Flow:
    id: str
    source: str
    target: str
    name: str = ""
    condition: str = ""


@dataclass
class Node:
    id: str
    type: str
    name: str = ""
    incoming: List[str] = field(default_factory=list)
    outgoing: List[str] = field(default_factory=list)
    default_flow: str = ""
    config: NodeConfig = field(default_factory=NodeConfig)
    wait_seconds: Optional[float] = None       # 타이머 이벤트
    attached_to: str = ""                      # 경계 이벤트가 붙은 노드
    is_error_boundary: bool = False
    trigger: str = ""                          # 시작 이벤트의 정의(timer, conditional, message …)
    scope: Optional["Scope"] = None            # 하위 프로세스의 안쪽 흐름


@dataclass
class Scope:
    """프로세스나 하위 프로세스 하나의 흐름."""
    id: str
    nodes: Dict[str, Node] = field(default_factory=dict)
    flows: Dict[str, Flow] = field(default_factory=dict)

    def start_nodes(self) -> List[Node]:
        """실행을 시작할 시작 이벤트.

        타이머·조건·메시지·신호 시작 이벤트는 해당 사건이 일어날 때 시작하는 흐름이므로,
        실행 요청(편집기·API 호출)으로는 일반(none) 시작 이벤트만 시작한다.
        일반 시작 이벤트가 하나도 없으면 모든 시작 이벤트로 시작한다.
        """
        starts = [n for n in self.nodes.values() if n.type == "startEvent" and not n.incoming]
        plain = [n for n in starts if not n.trigger]
        return plain or starts

    def error_boundary_of(self, node_id: str) -> Optional[Node]:
        for node in self.nodes.values():
            if node.type == "boundaryEvent" and node.attached_to == node_id and node.is_error_boundary:
                return node
        return None


def _float(value: Optional[str], default: float) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except ValueError:
        return default


def _int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value not in (None, "") else default
    except ValueError:
        return default


_DURATION = re.compile(
    r"^P(?:(?P<d>\d+(?:\.\d+)?)D)?(?:T(?:(?P<h>\d+(?:\.\d+)?)H)?(?:(?P<m>\d+(?:\.\d+)?)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?)?$"
)


def parse_duration(text: str) -> Optional[float]:
    """ISO 8601 기간(PT5S, PT1M30S 등)을 초로. 숫자만 있으면 초로 본다."""
    text = (text or "").strip().upper()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    match = _DURATION.match(text)
    if not match or text in ("P", "PT"):
        return None
    parts = {k: float(v) if v else 0.0 for k, v in match.groupdict().items()}
    return parts["d"] * 86400 + parts["h"] * 3600 + parts["m"] * 60 + parts["s"]


def _read_config(element: ET.Element) -> NodeConfig:
    config = NodeConfig()
    ext = element.find(_bpmn("extensionElements"))
    if ext is None:
        return config
    for params in ext:
        ns, local = _tag(params)
        if ns != PIPELINE_NS or local.lower() != "parameters":
            continue
        for item in params:
            ns, local = _tag(item)
            if ns != PIPELINE_NS:
                continue
            local = local.lower()
            if local == "parameter":
                # 처음 나온 parameter 만 실행 설정으로 쓴다(프런트엔드와 같은 규칙).
                if not config.url and item.get("url"):
                    config.url = item.get("url", "").strip()
                    config.method = (item.get("method") or "").strip().upper()
                    config.timeout = _float(item.get("timeout"), config.timeout)
                    config.retry = max(0, _int(item.get("retry"), config.retry))
                    config.delay = max(0.0, _float(item.get("delay"), config.delay))
            elif local == "input" and item.get("name"):
                config.inputs.append(InputSpec(
                    name=item.get("name", "").strip(),
                    source=(item.get("source") or "").strip(),
                    value=item.get("value"),
                ))
            elif local == "output" and item.get("name"):
                config.outputs.append(OutputSpec(
                    name=item.get("name", "").strip(),
                    path=(item.get("path") or "").strip(),
                ))
    return config


def _condition_text(flow_el: ET.Element) -> str:
    cond = flow_el.find(_bpmn("conditionExpression"))
    if cond is None:
        return ""
    return "".join(cond.itertext()).strip()


def _build_scope(container: ET.Element) -> Scope:
    scope = Scope(id=container.get("id", ""))
    for child in container:
        ns, local = _tag(child)
        if ns != BPMN_NS:
            continue
        if local == "sequenceFlow":
            flow = Flow(
                id=child.get("id", ""),
                source=child.get("sourceRef", ""),
                target=child.get("targetRef", ""),
                name=child.get("name", ""),
                condition=_condition_text(child),
            )
            scope.flows[flow.id] = flow
        elif local in FLOW_NODE_TAGS:
            node = Node(
                id=child.get("id", ""),
                type=local,
                name=child.get("name", ""),
                default_flow=child.get("default", ""),
                config=_read_config(child),
                attached_to=child.get("attachedToRef", ""),
            )
            if local in ("intermediateCatchEvent", "boundaryEvent"):
                timer = child.find(_bpmn("timerEventDefinition"))
                if timer is not None:
                    duration = timer.find(_bpmn("timeDuration"))
                    if duration is not None:
                        node.wait_seconds = parse_duration("".join(duration.itertext()))
            if local == "startEvent":
                for definition in child:
                    def_ns, def_local = _tag(definition)
                    if def_ns == BPMN_NS and def_local.endswith("EventDefinition"):
                        node.trigger = def_local[: -len("EventDefinition")]
                        break
            if local == "boundaryEvent":
                node.is_error_boundary = child.find(_bpmn("errorEventDefinition")) is not None
            if local in SCOPE_TAGS:
                node.scope = _build_scope(child)
            scope.nodes[node.id] = node

    # incoming/outgoing 는 요소에 적힌 참조보다 실제 흐름을 기준으로 다시 만든다.
    for flow in scope.flows.values():
        if flow.source in scope.nodes and flow.target in scope.nodes:
            scope.nodes[flow.source].outgoing.append(flow.id)
            scope.nodes[flow.target].incoming.append(flow.id)
    return scope


def parse(xml: str) -> List[Scope]:
    """BPMN XML 에서 실행할 프로세스 흐름들을 읽는다."""
    if not xml or not xml.strip():
        raise ModelError("BPMN XML 이 비어 있습니다.")
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    if len(data) > MAX_XML_BYTES:
        raise ModelError("BPMN XML 이 너무 큽니다.")
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        # 외부 엔티티·엔티티 확장 공격을 막는다. BPMN 에는 DTD 가 필요 없다.
        raise ModelError("DTD 가 포함된 XML 은 실행할 수 없습니다.")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ModelError(f"BPMN XML 을 해석할 수 없습니다: {exc}") from exc

    scopes = [_build_scope(p) for p in root.iter(_bpmn("process"))]
    scopes = [s for s in scopes if s.start_nodes()]
    if not scopes:
        raise ModelError("시작 이벤트가 있는 프로세스가 없습니다.")
    return scopes


# ---------------------------------------------------------------------------
# 실행 문맥
# ---------------------------------------------------------------------------

class Context:
    """실행 중 값 저장소.

    - variables: 실행 입력값과 노드 출력값(같은 이름이면 나중 값이 덮어쓴다)
    - nodes:     노드별 출력 묶음(`Task_1.PM10` 으로 참조)
    """

    def __init__(self, inputs: Optional[Mapping[str, Any]] = None):
        self.variables: Dict[str, Any] = dict(inputs or {})
        self.nodes: Dict[str, Dict[str, Any]] = {}

    def names(self) -> Dict[str, Any]:
        names = dict(self.variables)
        names.update(self.nodes)  # 노드 id 가 변수 이름보다 우선
        return names

    def set_outputs(self, node_id: str, outputs: Mapping[str, Any]) -> None:
        self.nodes[node_id] = dict(outputs)
        for key, value in outputs.items():
            if not key.startswith("_"):
                self.variables[key] = value


def _lookup_path(data: Any, path: str) -> Tuple[bool, Any]:
    """점으로 구분한 경로(`data.items.0.name`)로 값을 꺼낸다.

    `PM2.5` 처럼 이름 자체에 점이 있는 키는 통째로 먼저 찾는다.
    """
    if isinstance(data, Mapping) and path in data:
        return True, data[path]
    current = data
    for part in [p for p in path.split(".") if p != ""]:
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.lstrip("-").isdigit() and -len(current) <= int(part) < len(current):
            current = current[int(part)]
        else:
            return False, None
    return True, current


def unwrap(response: Any) -> Any:
    """`{"data": ...}` 로 감싼 응답(이 백엔드와 Strapi 형식)을 벗긴다."""
    if isinstance(response, Mapping) and "data" in response and set(response) <= {"data", "meta"}:
        return response["data"]
    return response


def extract_outputs(specs: List[OutputSpec], response: Any) -> Tuple[Dict[str, Any], List[str]]:
    """응답에서 출력값을 꺼낸다. (출력값, 경고)"""
    body = unwrap(response)
    warnings: List[str] = []
    if not specs:
        # 출력 정의가 없으면 응답의 최상위 키를 그대로 출력으로 쓴다.
        if isinstance(body, Mapping):
            return dict(body), warnings
        return ({"result": body} if body is not None else {}), warnings

    outputs: Dict[str, Any] = {}
    for spec in specs:
        path = spec.path or spec.name
        found, value = _lookup_path(response, path)
        if not found and body is not response:
            found, value = _lookup_path(body, path)
        if not found and not spec.path and isinstance(body, Mapping) and spec.name in body:
            found, value = True, body[spec.name]
        if not found:
            warnings.append(f"응답에 출력 '{spec.name}'({path}) 이(가) 없습니다.")
            value = None
        outputs[spec.name] = value
    return outputs, warnings


# ---------------------------------------------------------------------------
# 실행기
# ---------------------------------------------------------------------------

@dataclass
class CallResult:
    response: Any
    status_code: Optional[int] = None
    request: Dict[str, Any] = field(default_factory=dict)


Invoker = Callable[[NodeConfig, Dict[str, Any]], CallResult]


@dataclass
class StepRecord:
    seq: int
    node_id: str
    node_type: str
    node_name: str
    scope_id: str
    status: str = "succeeded"   # succeeded | failed | skipped
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    request: Dict[str, Any] = field(default_factory=dict)
    response: Any = None
    flows: List[str] = field(default_factory=list)   # 이 노드에서 나간 흐름
    warnings: List[str] = field(default_factory=list)
    error: str = ""
    attempts: int = 0
    started_at: str = ""
    duration_ms: int = 0


@dataclass
class RunResult:
    status: str                         # succeeded | failed
    variables: Dict[str, Any]
    nodes: Dict[str, Dict[str, Any]]
    steps: List[StepRecord]
    error: str = ""
    # 종료 이벤트에 입력(결과 정의)을 둔 경우 그 값. 로직을 API 로 호출했을 때의 응답 본문이다.
    result: Optional[Dict[str, Any]] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Engine:
    def __init__(
        self,
        invoker: Invoker,
        *,
        max_steps: int = DEFAULT_MAX_STEPS,
        max_wait_seconds: float = DEFAULT_MAX_WAIT_SECONDS,
        on_step: Optional[Callable[[StepRecord], None]] = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.invoker = invoker
        self.max_steps = max_steps
        self.max_wait_seconds = max_wait_seconds
        self.on_step = on_step
        self.sleep = sleep

    # -- 진입점 ------------------------------------------------------------

    def run(self, xml: str, inputs: Optional[Mapping[str, Any]] = None, start: str = "") -> RunResult:
        self.ctx = Context(inputs)
        self.steps: List[StepRecord] = []
        self.result: Optional[Dict[str, Any]] = None
        self._root_scope_id = ""
        try:
            scopes = parse(xml)
            scope, starts = self._select_start(scopes, start)
            self._root_scope_id = scope.id
            self._run_scope(scope, starts)
        except (ExecutionError, ModelError) as exc:
            return RunResult("failed", self.ctx.variables, self.ctx.nodes, self.steps, str(exc), self.result)
        return RunResult("succeeded", self.ctx.variables, self.ctx.nodes, self.steps, result=self.result)

    def _select_start(self, scopes: List[Scope], start: str) -> Tuple[Scope, List[Node]]:
        if start:
            for scope in scopes:
                node = scope.nodes.get(start)
                if node is not None:
                    if node.type != "startEvent":
                        raise ModelError(f"'{start}' 은(는) 시작 이벤트가 아닙니다.")
                    return scope, [node]
            raise ModelError(f"시작 이벤트 '{start}' 를 찾을 수 없습니다.")
        # 여러 프로세스(협업 다이어그램)면 첫 번째 프로세스를 실행한다.
        scope = scopes[0]
        return scope, scope.start_nodes()

    # -- 흐름 ----------------------------------------------------------------

    def _run_scope(self, scope: Scope, starts: List[Node]) -> None:
        queue: Deque[str] = deque(n.id for n in starts)
        arrivals: Dict[str, int] = {}
        waiting: Dict[str, int] = {}  # 포괄 합류에서 기다리는 토큰 수

        while queue or waiting:
            # 포괄 합류에 더 도착할 토큰이 없어졌으면(다른 가지가 끝났거나 선택되지 않음) 진행시킨다.
            for node_id in list(waiting):
                if not any(self._can_reach(scope, other, node_id) for other in queue if not other.startswith("fire:")):
                    del waiting[node_id]
                    queue.append(f"fire:{node_id}")

            item = queue.popleft()
            fired = item.startswith("fire:")
            node = scope.nodes[item[5:] if fired else item]

            if not fired and len(node.incoming) > 1:
                if node.type == "parallelGateway":
                    arrivals[node.id] = arrivals.get(node.id, 0) + 1
                    if arrivals[node.id] < len(node.incoming):
                        continue
                    arrivals[node.id] = 0
                elif node.type == "inclusiveGateway":
                    waiting[node.id] = waiting.get(node.id, 0) + 1
                    # 아직 이 합류에 도착할 수 있는 토큰이 남아 있으면 기다린다.
                    if any(self._can_reach(scope, other, node.id) for other in queue if not other.startswith("fire:")):
                        continue
                    del waiting[node.id]

            if len(self.steps) >= self.max_steps:
                raise ExecutionError(f"실행 단계가 {self.max_steps}개를 넘었습니다. 순환 흐름을 확인하세요.")

            for flow_id in self._execute(scope, node):
                queue.append(scope.flows[flow_id].target)

    def _can_reach(self, scope: Scope, source: str, target: str) -> bool:
        seen, stack = set(), [source]
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            node = scope.nodes.get(current)
            if node:
                stack.extend(scope.flows[f].target for f in node.outgoing)
        return False

    # -- 노드 ----------------------------------------------------------------

    def _execute(self, scope: Scope, node: Node) -> List[str]:
        """노드를 실행하고 이어갈 흐름 id 목록을 돌려준다."""
        step = StepRecord(
            seq=len(self.steps) + 1,
            node_id=node.id,
            node_type=node.type,
            node_name=node.name,
            scope_id=scope.id,
            started_at=_now(),
        )
        self.steps.append(step)
        began = time.monotonic()
        try:
            flows = self._dispatch(scope, node, step)
        except ExecutionError as exc:
            step.status = "failed"
            step.error = str(exc)
            boundary = scope.error_boundary_of(node.id)
            if boundary is None:
                self._finish(step, began)
                raise
            # 오류 경계 이벤트가 있으면 그쪽으로 이어간다.
            step.warnings.append(f"오류 경계 이벤트 '{boundary.name or boundary.id}' 로 이어갑니다.")
            self.ctx.set_outputs(node.id, {"_error": str(exc)})
            flows = list(boundary.outgoing)
        step.flows = flows
        self._finish(step, began)
        return flows

    def _finish(self, step: StepRecord, began: float) -> None:
        step.duration_ms = int((time.monotonic() - began) * 1000)
        if self.on_step:
            self.on_step(step)

    def _dispatch(self, scope: Scope, node: Node, step: StepRecord) -> List[str]:
        if node.type in GATEWAY_TAGS:
            return self._gateway(scope, node, step)

        if node.type == "boundaryEvent":
            # 경계 이벤트는 붙은 노드가 실패했을 때만 쓰인다.
            step.status = "skipped"
            return []

        if node.wait_seconds:
            wait = min(node.wait_seconds, self.max_wait_seconds)
            if wait < node.wait_seconds:
                step.warnings.append(f"대기 시간을 {self.max_wait_seconds:g}초로 줄였습니다.")
            self.sleep(wait)

        if node.scope is not None:
            starts = node.scope.start_nodes()
            if not starts:
                step.warnings.append("하위 프로세스에 시작 이벤트가 없어 건너뜁니다.")
            else:
                self._run_scope(node.scope, starts)

        if node.config.url:
            self._call(node, step)
        elif node.config.inputs and node.type in TASK_TAGS | {"endEvent"}:
            # URL 없이 입력만 정의한 노드는 값을 계산해 출력으로 남긴다(값 가공용).
            step.inputs = self._resolve_inputs(node, step)
            self.ctx.set_outputs(node.id, step.inputs)
            step.outputs = dict(step.inputs)
            if node.type == "endEvent" and scope.id == self._root_scope_id:
                self.result = {**(self.result or {}), **step.outputs}
        elif node.type in TASK_TAGS:
            step.status = "skipped"
            step.warnings.append("실행 URL 이 없어 통과합니다.")

        if node.type == "endEvent":
            return []
        return self._plain_outgoing(scope, node, step)

    def _plain_outgoing(self, scope: Scope, node: Node, step: StepRecord) -> List[str]:
        """게이트웨이가 아닌 노드: 조건 있는 흐름은 평가하고 나머지는 모두 따라간다."""
        chosen, defaults = [], []
        for flow_id in node.outgoing:
            flow = scope.flows[flow_id]
            if flow.id == node.default_flow:
                defaults.append(flow.id)
            elif not flow.condition or self._condition(flow, step):
                chosen.append(flow.id)
        return chosen or defaults

    def _condition(self, flow: Flow, step: StepRecord) -> bool:
        try:
            return bool(evaluate(flow.condition, self.ctx.names()))
        except ExpressionError as exc:
            step.warnings.append(f"흐름 '{flow.name or flow.id}' 조건을 거짓으로 처리했습니다: {exc}")
            return False

    def _gateway(self, scope: Scope, node: Node, step: StepRecord) -> List[str]:
        outgoing = [scope.flows[f] for f in node.outgoing]
        if node.type == "parallelGateway":
            return [f.id for f in outgoing]

        if node.type == "eventBasedGateway":
            if outgoing:
                step.warnings.append("이벤트 기반 게이트웨이는 첫 번째 흐름을 따릅니다.")
                return [outgoing[0].id]
            return []

        # 배타·포괄·복합 게이트웨이
        candidates = [f for f in outgoing if f.id != node.default_flow]
        if len(outgoing) <= 1:
            return [f.id for f in outgoing]  # 합류만 하는 게이트웨이

        matched: List[str] = []
        for flow in candidates:
            if not flow.condition:
                # 조건 없는 흐름은 항상 참으로 본다(토큰 시뮬레이션과 달리 사람이 고를 수 없다).
                step.warnings.append(f"흐름 '{flow.name or flow.id}' 에 조건이 없어 참으로 봅니다.")
                matched.append(flow.id)
            elif self._condition(flow, step):
                matched.append(flow.id)
            if matched and node.type == "exclusiveGateway":
                break

        if not matched and node.default_flow:
            matched = [node.default_flow]
        if not matched:
            raise ExecutionError(f"게이트웨이 '{node.name or node.id}' 에서 만족하는 흐름이 없습니다.")
        return matched

    # -- 호출 ----------------------------------------------------------------

    def _resolve_inputs(self, node: Node, step: StepRecord) -> Dict[str, Any]:
        names = self.ctx.names()
        values: Dict[str, Any] = {}
        for spec in node.config.inputs:
            if spec.source:
                try:
                    values[spec.name] = evaluate(spec.source, names)
                except ExpressionError as exc:
                    raise ExecutionError(f"입력 '{spec.name}' 을(를) 계산할 수 없습니다: {exc}") from exc
            elif spec.value is not None and spec.value != "":
                values[spec.name] = spec.value
            elif spec.name in self.ctx.variables:
                values[spec.name] = self.ctx.variables[spec.name]
            else:
                step.warnings.append(f"입력 '{spec.name}' 에 연결된 값이 없어 비워서 보냅니다.")
                continue
            # 같은 노드의 다음 입력 식에서 앞서 계산한 값을 쓸 수 있게 한다(지수 → 종합 점수 등).
            names[spec.name] = values[spec.name]
        return values

    def _call(self, node: Node, step: StepRecord) -> None:
        config = node.config
        step.inputs = self._resolve_inputs(node, step)
        if config.delay:
            self.sleep(min(config.delay, self.max_wait_seconds))

        last_error = ""
        for attempt in range(config.retry + 1):
            step.attempts = attempt + 1
            try:
                result = self.invoker(config, step.inputs)
            except ExecutionError as exc:
                last_error = str(exc)
                if attempt < config.retry:
                    self.sleep(min(2 ** attempt, 10))
                continue
            step.request = result.request
            step.response = result.response
            outputs, warnings = extract_outputs(config.outputs, result.response)
            step.outputs = outputs
            step.warnings.extend(warnings)
            self.ctx.set_outputs(node.id, outputs)
            return
        raise ExecutionError(last_error or "호출에 실패했습니다.")


def describe_interface(xml: str) -> Dict[str, List[str]]:
    """로직을 API 로 공개할 때의 입력·출력 이름.

    - inputs:  노드 입력 중 값 식·고정 값이 없고 앞선 노드 출력으로도 채워지지 않는 이름
               (호출하는 쪽이 넘겨야 하는 값)
    - outputs: 최상위 종료 이벤트에 정의한 결과 이름. 없으면 빈 목록(모든 값이 응답에 담김)
    """
    scopes = parse(xml)
    produced: set = set()
    wanted: List[str] = []
    result: List[str] = []

    def visit(scope: Scope, top: bool) -> None:
        for node in scope.nodes.values():
            produced.update(o.name for o in node.config.outputs)
            if node.type in TASK_TAGS | {"endEvent"} and not node.config.url:
                produced.update(i.name for i in node.config.inputs)  # 값 가공 노드
            for spec in node.config.inputs:
                if not spec.source and (spec.value is None or spec.value == "") and spec.name not in wanted:
                    wanted.append(spec.name)
            if top and node.type == "endEvent":
                result.extend(i.name for i in node.config.inputs if i.name not in result)
            if node.scope is not None:
                visit(node.scope, False)

    visit(scopes[0], True)
    return {"inputs": [n for n in wanted if n not in produced], "outputs": result}
