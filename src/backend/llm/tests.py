from unittest import mock

from django.test import SimpleTestCase

from . import local_llm


class CpuSupportTests(SimpleTestCase):
    def _with_flags(self, flags: str):
        data = f"processor\t: 0\nflags\t\t: {flags}\n\n"
        return mock.patch("builtins.open", mock.mock_open(read_data=data))

    def test_requires_avx2(self):
        with self._with_flags("fpu sse sse2 sse4_2"):   # 가상머신 기본 CPU 모델
            self.assertFalse(local_llm.cpu_supported())
            self.assertFalse(local_llm.is_available())
        with self._with_flags("fpu sse4_2 avx avx2 fma"):
            self.assertTrue(local_llm.cpu_supported())

    def test_force_override(self):
        with self._with_flags("fpu sse4_2"), mock.patch.dict("os.environ", {"LOCAL_LLM_FORCE": "1"}):
            self.assertTrue(local_llm.cpu_supported())


class OllamaFallbackTests(SimpleTestCase):
    def test_unreachable_config_falls_back_to_default_server(self):
        from types import SimpleNamespace
        from . import ollama_client, services

        config = SimpleNamespace(provider="ollama", base_url="http://down:11434", model_name="gpt-oss:20b",
                                 api_key="", enabled=True)
        reachable = lambda url=None, timeout=2.0: url == ollama_client.DEFAULT_BASE_URL
        plan = {"title": "대기 경보", "sources": [], "check": {"metric": "pm10", "op": ">", "threshold": 80, "label": "나쁨"},
                "alert_actions": ["SMS 알림 발송"], "extra_steps": [], "final_actions": []}
        with mock.patch.object(ollama_client, "is_reachable", side_effect=reachable), \
             mock.patch.object(ollama_client, "pick_model", return_value="qwen2.5:1.5b-instruct"), \
             mock.patch.object(services, "remote_provider_available", return_value=False), \
             mock.patch.object(local_llm, "is_available", return_value=False), \
             mock.patch.object(ollama_client, "generate_plan", return_value=plan) as gen:
            selected = services._select_engine("미세먼지가 나쁘면 알려줘", config)
        self.assertEqual(selected["engine"], "ollama")
        self.assertEqual(gen.call_args.args[1], "qwen2.5:1.5b-instruct")
        self.assertEqual(gen.call_args.args[4], ollama_client.DEFAULT_BASE_URL)


class PlannerTests(SimpleTestCase):
    """LLM 이 비우거나 틀린 plan 을 보정해 실행 가능한 spec 을 만드는지."""

    SOURCES = {
        "포항 대기 실데이터": {"url": "/api/fedit/objects/latest?fdt=F&fdo=O", "method": "GET",
                         "outputs": ["pm10", "pm25", "temp"], "inputs": [], "kind": "fedit"},
        "관광 디지털 트윈 시뮬레이션": {"url": "/api/pipelines/run?id=tour-flow", "method": "POST",
                             "outputs": ["방문객수", "혼잡도"], "inputs": ["관광지코드"], "kind": "catalog"},
        "관광지 쾌적지수 산출": {"url": "/api/pipelines/run?id=tour-comfort", "method": "POST",
                         "outputs": ["쾌적지수"], "inputs": ["혼잡도"], "kind": "catalog"},
    }

    def test_repairs_bad_model_output(self):
        from . import planner
        raw = {"title": "", "sources": ["없는 소스", "포항 대기 실데이터"],
               "check": {"metric": "미세먼지", "op": "?", "threshold": 0, "label": ""},
               "alert_actions": ["없는 동작"], "extra_steps": ["SMS 알림 발송"], "final_actions": []}
        plan = planner.normalize_plan(raw, "포항 미세먼지가 나쁘면 사이니지에 띄우고 기록해줘", self.SOURCES)
        self.assertEqual(plan["sources"], ["포항 대기 실데이터"])
        self.assertEqual((plan["check"]["metric"], plan["check"]["op"], plan["check"]["threshold"]), ("pm10", ">", 80))
        self.assertEqual(plan["alert_actions"], ["디지털 사이니지 표출"])
        self.assertEqual(plan["final_actions"], ["결과 저장"])
        self.assertEqual(plan["extra_steps"], [])

    def test_built_spec_runs_and_orders_dependencies(self):
        from pipelines.engine import CallResult, Engine
        from . import planner
        from .bpmn_spec import spec_to_bpmn_xml
        plan = planner.normalize_plan({"sources": ["관광지 쾌적지수 산출", "관광 디지털 트윈 시뮬레이션"]},
                                      "관광지가 혼잡하면 쾌적지수도 계산해서 문자로 알려줘", self.SOURCES)
        xml = spec_to_bpmn_xml(planner.build_spec(plan, self.SOURCES))
        calls = []

        def invoker(config, inputs):
            calls.append(config.url)
            return CallResult({"방문객수": 10, "혼잡도": 90, "쾌적지수": 40, "발송상태": "완료"})

        result = Engine(invoker, sleep=lambda s: None).run(xml, {})
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual(calls[:2], ["/api/pipelines/run?id=tour-flow", "/api/pipelines/run?id=tour-comfort"])
        self.assertIn("/api/pipelines/run?id=notify.sms", calls)            # 혼잡도 90 > 70 → 경보
        self.assertEqual(result.result["경보"], True)
