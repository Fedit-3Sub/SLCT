import time
from typing import Optional, Dict, Any
from .models import LlmConfig


def generate_with_llm(prompt: str, config: Optional[LlmConfig], diagram_uid: str = "") -> Dict[str, Any]:
    """
    Provider-agnostic generation stub.
    Later, branch by config.provider (ollama/openai/anthropic) and call real backends.
    For now, return a small BPMN snippet and basic metrics.
    """
    start = time.time()

    # Demo BPMN
    sample_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<bpmn:definitions xmlns:bpmn=\"http://www.omg.org/spec/BPMN/20100524/MODEL\" xmlns:bpmndi=\"http://www.omg.org/spec/BPMN/20100524/DI\" xmlns:di=\"http://www.omg.org/spec/DD/20100524/DI\" xmlns:dc=\"http://www.omg.org/spec/DD/20100524/DC\" id=\"Definitions_AI\" targetNamespace=\"http://bpmn.io/schema/bpmn\">\n"
        "  <bpmn:process id=\"Process_AI\" isExecutable=\"false\">\n"
        "    <bpmn:startEvent id=\"StartEvent_AI\" />\n"
        "  </bpmn:process>\n"
        "  <bpmndi:BPMNDiagram id=\"BPMNDiagram_AI\">\n"
        "    <bpmndi:BPMNPlane id=\"BPMNPlane_AI\" bpmnElement=\"Process_AI\">\n"
        "      <bpmndi:BPMNShape id=\"_BPMNShape_StartEvent_AI\" bpmnElement=\"StartEvent_AI\">\n"
        "        <dc:Bounds x=\"156\" y=\"82\" width=\"36\" height=\"36\" />\n"
        "      </bpmndi:BPMNShape>\n"
        "    </bpmndi:BPMNPlane>\n"
        "  </bpmndi:BPMNDiagram>\n"
        "</bpmn:definitions>\n"
    )

    # Very rough demo metrics
    tokens_in = max(1, len(prompt) // 4)
    tokens_out = 64
    duration_ms = int((time.time() - start) * 1000)

    return {
        "message": f"요청하신 요구사항을 바탕으로 다이어그램 초안을 생성했습니다. (uid={diagram_uid})",
        "generatedXml": sample_xml,
        "nodeSummary": "- 시작 이벤트로 시작하는 간단한 프로세스",
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": 0,
        "duration_ms": duration_ms,
    }
