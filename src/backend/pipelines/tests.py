from typing import Any, Dict, List

from django.test import SimpleTestCase, TestCase

from bpmns.models import BpmnDiagram

from .engine import CallResult, Engine, ExecutionError, NodeConfig, parse_duration
from .expressions import ExpressionError, evaluate
from .models import PipelineRun


def diagram(body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xmlns:pipeline="pipeline://" id="Definitions_1">
  <bpmn:process id="Process_1" isExecutable="true">
{body}
  </bpmn:process>
</bpmn:definitions>"""


def task(node_id: str, url: str = "", *, inputs: str = "", outputs: str = "", attrs: str = "", tag: str = "serviceTask") -> str:
    ext = ""
    if url or inputs or outputs:
        param = f'<pipeline:parameter url="{url}" {attrs}/>' if url else ""
        ext = f"<bpmn:extensionElements><pipeline:parameters>{param}{inputs}{outputs}</pipeline:parameters></bpmn:extensionElements>"
    return f'<bpmn:{tag} id="{node_id}" name="{node_id}">{ext}</bpmn:{tag}>'


def flow(flow_id: str, source: str, target: str, condition: str = "") -> str:
    cond = (f'<bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">{condition}</bpmn:conditionExpression>'
            if condition else "")
    return f'<bpmn:sequenceFlow id="{flow_id}" sourceRef="{source}" targetRef="{target}">{cond}</bpmn:sequenceFlow>'


class FakeInvoker:
    """URL 별로 정해둔 응답을 돌려주고 호출 내역을 남긴다."""

    def __init__(self, responses: Dict[str, Any]):
        self.responses = responses
        self.calls: List[tuple] = []

    def __call__(self, config: NodeConfig, inputs: Dict[str, Any]) -> CallResult:
        self.calls.append((config.url, dict(inputs)))
        response = self.responses[config.url]
        if isinstance(response, Exception):
            raise response
        if callable(response):
            response = response(inputs)
        return CallResult(response=response, request={"url": config.url})


def run(xml: str, responses: Dict[str, Any], inputs=None, **kwargs):
    invoker = FakeInvoker(responses)
    engine = Engine(invoker, sleep=lambda s: None, **kwargs)
    return engine.run(xml, inputs), invoker


class ExpressionTests(SimpleTestCase):
    def test_python_and_js_styles(self):
        names = {"PM10": "85", "등급": "나쁨", "Task_1": {"PM2.5": 40}}
        self.assertTrue(evaluate("PM10 > 80", names))           # 숫자 문자열 비교
        self.assertTrue(evaluate("${등급 == '나쁨'}", names))     # Camunda 감싸기, 한글 이름
        self.assertTrue(evaluate("PM10 > 80 && 등급 === '나쁨'", names))
        self.assertFalse(evaluate("!(PM10 > 80)", names))
        self.assertEqual(evaluate('Task_1["PM2.5"] * 2', names), 80)
        self.assertEqual(evaluate('var("등급")', names), "나쁨")
        self.assertEqual(evaluate("'a && b'", names), "a && b")  # 문자열 안은 바꾸지 않는다

    def test_rejects_unsafe(self):
        for source in ["__import__('os')", "().__class__", "open('x')", "[x for x in y]", "lambda: 1"]:
            with self.assertRaises(ExpressionError, msg=source):
                evaluate(source, {"y": []})
        with self.assertRaises(ExpressionError):
            evaluate("없는값 > 1", {})

    def test_duration(self):
        self.assertEqual(parse_duration("PT1M30S"), 90)
        self.assertEqual(parse_duration("5"), 5)
        self.assertIsNone(parse_duration("PT"))


class EngineTests(SimpleTestCase):
    def test_passes_outputs_to_next_node(self):
        xml = diagram(
            '<bpmn:startEvent id="S"/>'
            + task("A", "http://a", outputs='<pipeline:output name="PM10" path="data.pm10"/>')
            + task("B", "http://b",
                   inputs='<pipeline:input name="농도" source="A.PM10"/>'
                          '<pipeline:input name="지역" value="포항"/>'
                          '<pipeline:input name="기온"/>')
            + '<bpmn:endEvent id="E"/>'
            + flow("f1", "S", "A") + flow("f2", "A", "B") + flow("f3", "B", "E")
        )
        result, invoker = run(xml, {"http://a": {"data": {"pm10": 92}}, "http://b": {"ok": True}}, {"기온": 21})
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual(invoker.calls[1], ("http://b", {"농도": 92, "지역": "포항", "기온": 21}))
        self.assertEqual(result.variables["PM10"], 92)
        self.assertEqual(result.nodes["B"], {"ok": True})
        self.assertEqual([s.node_id for s in result.steps], ["S", "A", "B", "E"])

    def test_exclusive_gateway_condition_and_default(self):
        body = (
            '<bpmn:startEvent id="S"/>'
            + task("A", "http://a")
            + '<bpmn:exclusiveGateway id="G" default="f_ok"/>'
            + task("Alert", "http://alert") + task("Ok", "http://ok")
            + flow("f1", "S", "A") + flow("f2", "A", "G")
            + flow("f_bad", "G", "Alert", "PM10 &gt; 80") + flow("f_ok", "G", "Ok")
        )
        responses = {"http://a": lambda i: {"PM10": 95}, "http://alert": {}, "http://ok": {}}
        result, _ = run(diagram(body), responses)
        self.assertIn("Alert", [s.node_id for s in result.steps])
        self.assertNotIn("Ok", [s.node_id for s in result.steps])

        responses["http://a"] = {"PM10": 30}
        result, _ = run(diagram(body), responses)
        self.assertIn("Ok", [s.node_id for s in result.steps])
        self.assertNotIn("Alert", [s.node_id for s in result.steps])

    def test_exclusive_without_match_fails(self):
        body = (
            '<bpmn:startEvent id="S"/><bpmn:exclusiveGateway id="G"/>'
            + task("A", "http://a") + task("B", "http://b")
            + flow("f1", "S", "G") + flow("f2", "G", "A", "x == 1") + flow("f3", "G", "B", "x == 2")
        )
        result, _ = run(diagram(body), {"http://a": {}, "http://b": {}}, {"x": 3})
        self.assertEqual(result.status, "failed")
        self.assertIn("만족하는 흐름이 없습니다", result.error)

    def test_parallel_fork_and_join(self):
        body = (
            '<bpmn:startEvent id="S"/><bpmn:parallelGateway id="Fork"/><bpmn:parallelGateway id="Join"/>'
            + task("A", "http://a") + task("B", "http://b")
            + task("C", "http://c", inputs='<pipeline:input name="a" source="A.v"/><pipeline:input name="b" source="B.v"/>')
            + '<bpmn:endEvent id="E"/>'
            + flow("f1", "S", "Fork") + flow("f2", "Fork", "A") + flow("f3", "Fork", "B")
            + flow("f4", "A", "Join") + flow("f5", "B", "Join") + flow("f6", "Join", "C") + flow("f7", "C", "E")
        )
        result, invoker = run(diagram(body), {"http://a": {"v": 1}, "http://b": {"v": 2}, "http://c": {}})
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual([c for c in invoker.calls if c[0] == "http://c"], [("http://c", {"a": 1, "b": 2})])
        self.assertEqual([s.node_id for s in result.steps].count("Join"), 1)

    def test_inclusive_join_waits_only_for_taken_branches(self):
        body = (
            '<bpmn:startEvent id="S"/><bpmn:inclusiveGateway id="Fork"/><bpmn:inclusiveGateway id="Join"/>'
            + task("A", "http://a") + task("B", "http://b") + task("C", "http://c") + task("D", "http://d")
            + flow("f1", "S", "Fork")
            + flow("f2", "Fork", "A", "x &gt; 0") + flow("f3", "Fork", "B", "x &gt; 5") + flow("f4", "Fork", "C", "x &gt; 100")
            + flow("f5", "A", "Join") + flow("f6", "B", "Join") + flow("f7", "C", "Join") + flow("f8", "Join", "D")
        )
        responses = {u: {} for u in ("http://a", "http://b", "http://c", "http://d")}
        result, invoker = run(diagram(body), responses, {"x": 10})
        self.assertEqual(result.status, "succeeded", result.error)
        urls = [c[0] for c in invoker.calls]
        self.assertEqual(sorted(urls[:2]), ["http://a", "http://b"])
        self.assertEqual(urls[2:], ["http://d"])

    def test_subprocess_runs_inner_flow(self):
        body = (
            '<bpmn:startEvent id="S"/>'
            '<bpmn:subProcess id="Sub"><bpmn:startEvent id="SS"/>'
            + task("Inner", "http://inner") + '<bpmn:endEvent id="SE"/>'
            + flow("s1", "SS", "Inner") + flow("s2", "Inner", "SE")
            + "</bpmn:subProcess>"
            + task("After", "http://after", inputs='<pipeline:input name="v" source="Inner.v"/>')
            + flow("f1", "S", "Sub") + flow("f2", "Sub", "After")
        )
        result, invoker = run(diagram(body), {"http://inner": {"v": 7}, "http://after": {}})
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual(invoker.calls[-1], ("http://after", {"v": 7}))

    def test_retry_then_error_boundary(self):
        body = (
            '<bpmn:startEvent id="S"/>'
            + task("A", "http://a", attrs='retry="2"')
            + '<bpmn:boundaryEvent id="Err" attachedToRef="A"><bpmn:errorEventDefinition/></bpmn:boundaryEvent>'
            + task("Fallback", "http://fb")
            + flow("f1", "S", "A") + flow("f2", "Err", "Fallback")
        )
        result, invoker = run(diagram(body), {"http://a": ExecutionError("down"), "http://fb": {}})
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual([c[0] for c in invoker.calls], ["http://a"] * 3 + ["http://fb"])
        step_a = next(s for s in result.steps if s.node_id == "A")
        self.assertEqual((step_a.status, step_a.attempts), ("failed", 3))

    def test_failure_without_boundary_fails_run(self):
        body = '<bpmn:startEvent id="S"/>' + task("A", "http://a") + flow("f1", "S", "A")
        result, _ = run(diagram(body), {"http://a": ExecutionError("down")})
        self.assertEqual(result.status, "failed")
        self.assertIn("down", result.error)

    def test_loop_guard(self):
        body = '<bpmn:startEvent id="S"/>' + task("A") + task("B") + flow("f1", "S", "A") + flow("f2", "A", "B") + flow("f3", "B", "A")
        result, _ = run(diagram(body), {}, max_steps=50)
        self.assertEqual(result.status, "failed")
        self.assertIn("50", result.error)

    def test_rejects_dtd(self):
        xml = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]>' + diagram('<bpmn:startEvent id="S"/>')[38:]
        result, _ = run(xml, {})
        self.assertEqual(result.status, "failed")
        self.assertIn("DTD", result.error)


class ExecuteApiTests(TestCase):
    XML = diagram(
        '<bpmn:startEvent id="S"/>'
        + task("Tour", "/api/pipelines/run?id=tour-flow")
        + task("Comfort", "/api/pipelines/run?id=tour-comfort",
               inputs='<pipeline:input name="혼잡도"/><pipeline:input name="기온" value="24"/>')
        + '<bpmn:endEvent id="E"/>'
        + flow("f1", "S", "Tour") + flow("f2", "Tour", "Comfort") + flow("f3", "Comfort", "E")
    )

    def test_execute_with_mock_catalog_nodes(self):
        BpmnDiagram.objects.create(uid="d1", xml=self.XML)
        resp = self.client.post("/api/pipelines/execute", {"uid": "d1", "wait": True}, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "succeeded", data["error"])
        tour, comfort = data["steps"][1], data["steps"][2]
        self.assertIn("혼잡도", tour["outputs"])
        # 앞 노드의 혼잡도가 이름으로 자동 연결된다.
        self.assertEqual(comfort["inputs"]["혼잡도"], tour["outputs"]["혼잡도"])
        self.assertEqual(comfort["inputs"]["기온"], "24")

        listing = self.client.get("/api/pipelines/runs?diagram=d1").json()
        self.assertEqual(listing["meta"]["count"], 1)
        detail = self.client.get(f"/api/pipelines/runs/{data['id']}").json()["data"]
        self.assertEqual(len(detail["steps"]), 4)

    def test_rejects_bad_requests(self):
        resp = self.client.post("/api/pipelines/execute", {}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post("/api/pipelines/execute", {"xml": "<x/>"}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(PipelineRun.objects.count(), 0)


FEDIT_ROW = {
    "federated_digital_object_id": "KR-104111-0109",
    "rowtime": "2026-09-30T02:25:04.204Z",
    "data": {
        "KR-104111-0024": {
            "id": "urn:ngsi-ld:Atmosphere:KR-104111-0021",
            "pm10": {"type": "Property", "value": 45.8, "observedAt": "2026-09-30T02:15:10.000Z"},
            "temp": {"type": "Property", "value": 28.3, "observedAt": "2026-09-30T02:15:10.000Z"},
            "location": {"type": "GeoProperty", "value": {"type": "Point", "coordinates": [0, 0]}},
        },
        "KR-104111-0025": {
            "pm10": {"type": "Property", "value": 50.2},
            "weatherMeasurement": [
                {"date_time": "2025-11-03 06:00:00", "temperature": 8},
                {"date_time": "2025-11-03 07:00:00", "temperature": 10, "sky_status": "1"},
            ],
        },
    },
}


class BrainFlattenTests(SimpleTestCase):
    def test_flatten_ngsi_ld_row(self):
        from digitaltwins.brain import flatten_row
        flat = flatten_row(FEDIT_ROW)
        self.assertEqual(flat["pm10"], 48.0)                   # 두 디지털객체 평균
        self.assertEqual(flat["KR-104111-0024.pm10"], 45.8)    # 전체 이름도 유지
        self.assertEqual(flat["temp"], 28.3)
        self.assertEqual(flat["temperature"], 10)              # 측정값 배열은 최근 시각 값
        self.assertEqual(flat["observedAt"], "2026-09-30T02:15:10.000Z")


def logic_diagram(end_inputs: str = "") -> str:
    end = (f'<bpmn:endEvent id="E"><bpmn:extensionElements><pipeline:parameters>{end_inputs}'
           '</pipeline:parameters></bpmn:extensionElements></bpmn:endEvent>') if end_inputs else '<bpmn:endEvent id="E"/>'
    return diagram(
        '<bpmn:startEvent id="S"/><bpmn:exclusiveGateway id="G" default="f_ok"/>'
        + task("Alert", "/api/pipelines/run?id=notify.signage",
               inputs='<pipeline:input name="표출문구" source="\'미세먼지 \' + str(pm10)"/>',
               outputs='<pipeline:output name="표출상태"/>')
        + end
        + flow("f1", "S", "G") + flow("f_bad", "G", "Alert", "pm10 &gt; 40") + flow("f_ok", "G", "E")
        + flow("f2", "Alert", "E")
    )


class LogicApiTests(TestCase):
    def test_invoke_with_fedit_simulation_payload(self):
        xml = logic_diagram('<pipeline:input name="경보" source="pm10 &gt; 40"/><pipeline:input name="pm10"/>')
        BpmnDiagram.objects.create(uid="air", title="대기 경보", xml=xml)
        body = {"simulation_id": "SIM1", "federated_digital_twin_id": "FDT1", "input_data": [FEDIT_ROW]}
        resp = self.client.post("/api/logics/air/invoke", body, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()["data"]
        self.assertEqual(data["result"], {"경보": True, "pm10": 48.0})
        run = PipelineRun.objects.get(pk=data["runId"])
        self.assertEqual(run.trigger, "fedit")
        self.assertIn("Alert", [s.node_id for s in run.steps.all()])

    def test_invoke_plain_json_and_failure(self):
        BpmnDiagram.objects.create(uid="air2", xml=logic_diagram())
        resp = self.client.post("/api/logics/air2/invoke", {"pm10": 10}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["result"]["pm10"], 10)   # 결과 정의가 없으면 전체 값
        # pm10 이 없으면 조건을 거짓으로 보고 기본 흐름으로 간다
        resp = self.client.post("/api/logics/air2/invoke", {}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.post("/api/logics/none/invoke", {}, content_type="application/json").status_code, 404)

    def test_spec_lists_external_inputs_and_results(self):
        xml = diagram(
            '<bpmn:startEvent id="S"/>'
            + task("A", "http://a", inputs='<pipeline:input name="지역코드"/>', outputs='<pipeline:output name="pm10"/>')
            + task("B", "http://b", inputs='<pipeline:input name="pm10"/><pipeline:input name="기준" value="35"/>')
            + '<bpmn:endEvent id="E"><bpmn:extensionElements><pipeline:parameters>'
              '<pipeline:input name="등급" source="\'나쁨\' if pm10 &gt; 35 else \'보통\'"/>'
              '</pipeline:parameters></bpmn:extensionElements></bpmn:endEvent>'
            + flow("f1", "S", "A") + flow("f2", "A", "B") + flow("f3", "B", "E")
        )
        BpmnDiagram.objects.create(uid="spec1", title="대기 등급", xml=xml)
        spec = self.client.get("/api/logics/spec1/spec").json()
        post = spec["paths"]["/api/logics/spec1/invoke"]["post"]
        self.assertEqual(list(post["requestBody"]["content"]["application/json"]["schema"]["properties"]), ["지역코드"])
        result = post["responses"]["200"]["content"]["application/json"]["schema"]["properties"]["data"]["properties"]["result"]
        self.assertEqual(list(result["properties"]), ["등급"])
        listing = self.client.get("/api/logics").json()["data"]
        self.assertEqual(listing[0]["inputs"], ["지역코드"])

    def test_fedit_registration_payload(self):
        from unittest import mock
        BpmnDiagram.objects.create(uid="reg", title="대기 경보", xml=logic_diagram())
        with mock.patch("digitaltwins.brain.register_simulation", return_value={"simulation_id": "S9"}) as reg:
            resp = self.client.post("/api/logics/reg/fedit",
                                    {"fdt": "FDT1", "subjects": ["KR-104111-0109"], "timeStep": 2},
                                    content_type="application/json", HTTP_HOST="slct.example.org")
        self.assertEqual(resp.status_code, 201, resp.content)
        fdt, payload = reg.call_args.args
        self.assertEqual(fdt, "FDT1")
        self.assertEqual(payload["simulation_access_url"], "http://slct.example.org/api/logics/reg/invoke")
        self.assertEqual(payload["simulation_subject"], ["KR-104111-0109"])
        self.assertEqual(payload["time_step"], 2)
        self.assertEqual(BpmnDiagram.objects.get(uid="reg").metadata["fedit"]["fdt"], "FDT1")


class EntryAndInputTests(SimpleTestCase):
    def test_plain_start_events_take_priority(self):
        body = (
            '<bpmn:startEvent id="Timer"><bpmn:timerEventDefinition/></bpmn:startEvent>'
            '<bpmn:startEvent id="Plain"/>'
            + task("A", "http://a") + task("B", "http://b")
            + flow("f1", "Timer", "A") + flow("f2", "Plain", "B")
        )
        result, invoker = run(diagram(body), {"http://a": {}, "http://b": {}})
        self.assertEqual([c[0] for c in invoker.calls], ["http://b"])

    def test_inputs_see_earlier_inputs_and_defaults(self):
        body = (
            '<bpmn:startEvent id="S"/>'
            + task("Calc", inputs='<pipeline:input name="a" source="var(\'x\', 10) * 2"/>'
                                  '<pipeline:input name="b" source="a + 1"/>', tag="task")
            + flow("f1", "S", "Calc")
        )
        result, _ = run(diagram(body), {})
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual((result.variables["a"], result.variables["b"]), (20, 21))


class EditTokenTests(TestCase):
    def setUp(self):
        from unittest import mock
        patcher = mock.patch.dict("os.environ", {"SLCT_EDIT_TOKEN": "secret-token"})
        patcher.start()
        self.addCleanup(patcher.stop)
        BpmnDiagram.objects.create(uid="open", xml=logic_diagram())

    def test_reads_public_writes_need_token(self):
        new = {"data": {"uid": "t1", "xml": logic_diagram()}}
        self.assertEqual(self.client.get("/api/bpmns").status_code, 200)
        self.assertEqual(self.client.post("/api/bpmns", new, content_type="application/json").status_code, 403)
        self.assertEqual(self.client.post("/api/bpmns", new, content_type="application/json",
                                          HTTP_X_SLCT_TOKEN="wrong").status_code, 403)
        self.assertEqual(self.client.post("/api/bpmns", new, content_type="application/json",
                                          HTTP_X_SLCT_TOKEN="secret-token").status_code, 201)
        self.assertEqual(self.client.post("/api/pipelines/execute?token=secret-token", {"uid": "open", "wait": True},
                                          content_type="application/json").status_code, 200)
        self.assertEqual(self.client.post("/api/pipelines/execute", {"uid": "open"},
                                          content_type="application/json").status_code, 403)

    def test_invoke_stays_public_and_check_endpoint(self):
        self.assertEqual(self.client.post("/api/logics/open/invoke", {}, content_type="application/json").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/edit").json()["data"], {"required": True, "editable": False})
        self.assertEqual(self.client.get("/api/auth/edit", HTTP_X_SLCT_TOKEN="secret-token").json()["data"]["editable"], True)
