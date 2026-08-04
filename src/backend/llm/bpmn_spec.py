"""프로세스 명세(spec) → BPMN XML 변환기.

LLM 경로와 규칙 기반 경로가 **같은 spec 구조**를 만들고, 이 모듈이 그것을
결정적으로 BPMN XML 로 조립한다. 덕분에 어느 경로를 타든 XML 이 항상 유효하다.

spec 예시::

    {
        "name": "관광지 혼잡 대응",
        "nodes": [
            {"id": "n1", "type": "startEvent",       "name": "관측 시작"},
            {"id": "n2", "type": "serviceTask",      "name": "기상 센서 수집"},
            {"id": "n3", "type": "exclusiveGateway", "name": "혼잡 임계 초과?"},
            {"id": "n4", "type": "endEvent",         "name": "종료"}
        ],
        "flows": [
            {"from": "n1", "to": "n2"},
            {"from": "n3", "to": "n4", "name": "예"}
        ]
    }

좌표(BPMNDI)는 일부러 생성하지 않는다. 프런트엔드가 좌표 없는 XML 을 받으면
자동 레이아웃으로 노드를 배치하므로, 모델은 흐름 구조에만 집중하면 된다.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape as _escape

# 이름은 모두 XML **속성값**으로 들어가므로 따옴표까지 이스케이프해야 한다.
# saxutils.escape() 는 기본적으로 & < > 만 처리하여 따옴표가 든 이름에서 XML 이 깨진다.
_ATTR_ENTITIES = {'"': "&quot;", "'": "&apos;"}


def xml_escape(value: str) -> str:
    return _escape(str(value), _ATTR_ENTITIES)

# 허용하는 노드 타입 → BPMN 엘리먼트 이름
NODE_TYPES: Dict[str, str] = {
    "startEvent": "bpmn:startEvent",
    "endEvent": "bpmn:endEvent",
    "task": "bpmn:task",
    "serviceTask": "bpmn:serviceTask",
    "userTask": "bpmn:userTask",
    "sendTask": "bpmn:sendTask",
    "receiveTask": "bpmn:receiveTask",
    "exclusiveGateway": "bpmn:exclusiveGateway",
    "parallelGateway": "bpmn:parallelGateway",
}

# 모델이 흔히 쓰는 표기 흔들림을 표준 타입으로 흡수한다.
TYPE_ALIASES: Dict[str, str] = {
    "start": "startEvent",
    "startevent": "startEvent",
    "end": "endEvent",
    "endevent": "endEvent",
    "service": "serviceTask",
    "servicetask": "serviceTask",
    "user": "userTask",
    "usertask": "userTask",
    "send": "sendTask",
    "sendtask": "sendTask",
    "receive": "receiveTask",
    "receivetask": "receiveTask",
    "gateway": "exclusiveGateway",
    "exclusive": "exclusiveGateway",
    "exclusivegateway": "exclusiveGateway",
    "xor": "exclusiveGateway",
    "parallel": "parallelGateway",
    "parallelgateway": "parallelGateway",
    "and": "parallelGateway",
    "activity": "task",
}

_ID_INVALID = re.compile(r"[^A-Za-z0-9_.-]")

DEFINITIONS_ATTRS = (
    'xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
    'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
    'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
    'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
    'targetNamespace="http://bpmn.io/schema/bpmn"'
)


def normalize_type(raw: Any) -> str:
    """임의의 타입 표기를 허용된 노드 타입으로 정규화한다."""
    if not isinstance(raw, str):
        return "task"
    value = raw.strip()
    if value in NODE_TYPES:
        return value
    key = value.replace("bpmn:", "").replace("_", "").replace("-", "").replace(" ", "").lower()
    if key in TYPE_ALIASES:
        return TYPE_ALIASES[key]
    for allowed in NODE_TYPES:
        if allowed.lower() == key:
            return allowed
    return "task"


def sanitize_id(raw: Any, fallback: str) -> str:
    """BPMN id 는 xsd:ID(NCName) 규칙을 따라야 한다 — 숫자로 시작 불가."""
    value = str(raw).strip() if raw is not None else ""
    value = _ID_INVALID.sub("_", value)
    if not value or not (value[0].isalpha() or value[0] == "_"):
        value = f"{fallback}_{value}" if value else fallback
    return value


def _clean_name(raw: Any) -> str:
    if raw is None:
        return ""
    # 줄바꿈/제어문자는 라벨을 깨뜨리므로 공백으로 접는다.
    return re.sub(r"\s+", " ", str(raw)).strip()[:120]


def normalize_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """느슨한 spec 을 안전한 형태로 다듬는다.

    - 알 수 없는 타입은 task 로
    - id 중복/누락 보정, 존재하지 않는 노드를 가리키는 flow 제거
    - 시작/종료 이벤트가 없으면 보충
    """
    raw_nodes = spec.get("nodes") if isinstance(spec, dict) else None
    raw_flows = spec.get("flows") if isinstance(spec, dict) else None
    raw_nodes = raw_nodes if isinstance(raw_nodes, list) else []
    raw_flows = raw_flows if isinstance(raw_flows, list) else []

    nodes: List[Dict[str, str]] = []
    seen_ids: Dict[str, str] = {}  # 원본 id → 확정 id
    used: set = set()

    for index, item in enumerate(raw_nodes):
        if not isinstance(item, dict):
            continue
        node_type = normalize_type(item.get("type"))
        original = item.get("id")
        node_id = sanitize_id(original, f"Node_{index + 1}")
        while node_id in used:
            node_id = f"{node_id}_{index + 1}"
        used.add(node_id)
        if original is not None:
            seen_ids.setdefault(str(original), node_id)
        seen_ids.setdefault(node_id, node_id)
        nodes.append({"id": node_id, "type": node_type, "name": _clean_name(item.get("name"))})

    if not nodes:
        nodes = [
            {"id": "StartEvent_1", "type": "startEvent", "name": "시작"},
            {"id": "Task_1", "type": "task", "name": "작업"},
            {"id": "EndEvent_1", "type": "endEvent", "name": "종료"},
        ]
        seen_ids.update({n["id"]: n["id"] for n in nodes})
        used.update(n["id"] for n in nodes)

    # 시작/종료 이벤트 보충 — 모델이 자주 빠뜨린다.
    if not any(n["type"] == "startEvent" for n in nodes):
        start_id = "StartEvent_1"
        while start_id in used:
            start_id += "_1"
        used.add(start_id)
        nodes.insert(0, {"id": start_id, "type": "startEvent", "name": "시작"})
        seen_ids.setdefault(start_id, start_id)
    if not any(n["type"] == "endEvent" for n in nodes):
        end_id = "EndEvent_1"
        while end_id in used:
            end_id += "_1"
        used.add(end_id)
        nodes.append({"id": end_id, "type": "endEvent", "name": "종료"})
        seen_ids.setdefault(end_id, end_id)

    valid_ids = {n["id"] for n in nodes}
    flows: List[Dict[str, str]] = []
    flow_seen: set = set()

    for index, item in enumerate(raw_flows):
        if not isinstance(item, dict):
            continue
        src_raw = item.get("from", item.get("source", item.get("sourceRef")))
        dst_raw = item.get("to", item.get("target", item.get("targetRef")))
        src = seen_ids.get(str(src_raw)) or sanitize_id(src_raw, "")
        dst = seen_ids.get(str(dst_raw)) or sanitize_id(dst_raw, "")
        # 존재하지 않는 노드를 가리키는 연결은 버린다(끊어진 다이어그램 방지).
        if src not in valid_ids or dst not in valid_ids or src == dst:
            continue
        if (src, dst) in flow_seen:
            continue
        flow_seen.add((src, dst))
        flows.append({
            "id": f"Flow_{len(flows) + 1}",
            "from": src,
            "to": dst,
            "name": _clean_name(item.get("name")),
        })

    # 연결이 하나도 없으면 노드를 나열된 순서대로 직렬 연결한다.
    if not flows and len(nodes) > 1:
        for i in range(len(nodes) - 1):
            flows.append({
                "id": f"Flow_{i + 1}",
                "from": nodes[i]["id"],
                "to": nodes[i + 1]["id"],
                "name": "",
            })
    elif flows:
        # 소형 모델은 노드보다 연결을 적게 만들어 고립 노드를 남기는 일이 잦다.
        # 아무 연결도 없는 노드를 종료 이벤트 직전에 이어 붙여 흐름을 하나로 잇는다.
        degree = {n["id"]: 0 for n in nodes}
        for flow in flows:
            degree[flow["from"]] += 1
            degree[flow["to"]] += 1
        end_ids = [n["id"] for n in nodes if n["type"] == "endEvent"]
        end_id = end_ids[-1] if end_ids else None
        orphans = [n["id"] for n in nodes if degree[n["id"]] == 0 and n["id"] != end_id]

        if orphans:
            into_end = [f for f in flows if end_id and f["to"] == end_id]
            if into_end:
                # (앵커 → 종료) 연결을 끊고 (앵커 → 고립노드들 → 종료) 로 재배선한다.
                bridge = into_end[-1]
                anchor = bridge["from"]
                flows.remove(bridge)
            else:
                # 종료로 들어오는 연결이 없으면 흐름의 끝(나가는 연결이 없는 노드)에 잇는다.
                sources = {f["from"] for f in flows}
                tails = [n["id"] for n in nodes
                         if degree[n["id"]] > 0 and n["id"] not in sources and n["id"] != end_id]
                anchor = tails[-1] if tails else flows[-1]["to"]

            prev = anchor
            for orphan in orphans:
                flows.append({"id": "", "from": prev, "to": orphan, "name": ""})
                prev = orphan
            if end_id:
                flows.append({"id": "", "from": prev, "to": end_id, "name": ""})

        # 재배선 후 흐름 id 를 다시 매긴다.
        for index, flow in enumerate(flows):
            flow["id"] = f"Flow_{index + 1}"

    name = _clean_name(spec.get("name") if isinstance(spec, dict) else "") or "생성된 프로세스"
    return {"name": name, "nodes": nodes, "flows": flows}


def spec_to_bpmn_xml(spec: Dict[str, Any], process_id: str = "Process_AI") -> str:
    """spec 을 BPMN 2.0 XML 로 변환한다(좌표 없음 — 프런트가 자동 배치)."""
    data = normalize_spec(spec)
    nodes, flows = data["nodes"], data["flows"]

    incoming: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    outgoing: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    for flow in flows:
        outgoing[flow["from"]].append(flow["id"])
        incoming[flow["to"]].append(flow["id"])

    lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<bpmn:definitions {DEFINITIONS_ATTRS} id="Definitions_AI">',
        f'  <bpmn:process id="{process_id}" name="{xml_escape(data["name"])}" isExecutable="false">',
    ]

    for node in nodes:
        tag = NODE_TYPES[node["type"]]
        attrs = f'id="{node["id"]}"'
        if node["name"]:
            attrs += f' name="{xml_escape(node["name"])}"'
        refs = [f"    <bpmn:incoming>{fid}</bpmn:incoming>" for fid in incoming[node["id"]]]
        refs += [f"    <bpmn:outgoing>{fid}</bpmn:outgoing>" for fid in outgoing[node["id"]]]
        if refs:
            lines.append(f"    <{tag} {attrs}>")
            lines.extend(refs)
            lines.append(f"    </{tag}>")
        else:
            lines.append(f"    <{tag} {attrs} />")

    for flow in flows:
        attrs = f'id="{flow["id"]}" sourceRef="{flow["from"]}" targetRef="{flow["to"]}"'
        if flow["name"]:
            attrs += f' name="{xml_escape(flow["name"])}"'
        lines.append(f"    <bpmn:sequenceFlow {attrs} />")

    lines.append("  </bpmn:process>")
    lines.append("</bpmn:definitions>")
    lines.append("")
    return "\n".join(lines)


def summarize_spec(spec: Dict[str, Any]) -> str:
    """사이드바에 표시할 노드 요약 문자열."""
    data = normalize_spec(spec)
    labels = {
        "startEvent": "시작 이벤트",
        "endEvent": "종료 이벤트",
        "task": "작업",
        "serviceTask": "서비스 작업",
        "userTask": "사용자 작업",
        "sendTask": "전송 작업",
        "receiveTask": "수신 작업",
        "exclusiveGateway": "배타 게이트웨이",
        "parallelGateway": "병렬 게이트웨이",
    }
    rows = [
        f"- {node['name'] or labels.get(node['type'], node['type'])} ({labels.get(node['type'], node['type'])})"
        for node in data["nodes"]
    ]
    rows.append(f"- 연결 {len(data['flows'])}개")
    return "\n".join(rows)


def parse_spec_json(text: str) -> Optional[Dict[str, Any]]:
    """모델 출력에서 spec JSON 을 추출한다. 실패하면 None."""
    import json

    if not text:
        return None
    candidate = text.strip()
    # ```json ... ``` 코드펜스 제거
    fence = re.search(r"```(?:json)?\s*(.+?)```", candidate, re.S)
    if fence:
        candidate = fence.group(1).strip()
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = candidate[start:end + 1]
    try:
        parsed = json.loads(candidate)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None
