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
        with mock.patch.object(ollama_client, "is_reachable", side_effect=reachable), \
             mock.patch.object(ollama_client, "pick_model", return_value="qwen2.5:1.5b-instruct"), \
             mock.patch.object(services, "remote_provider_available", return_value=False), \
             mock.patch.object(ollama_client, "generate_spec", return_value={"name": "x", "nodes": [], "flows": []}) as gen:
            selected = services._select_engine("테스트", config)
        self.assertEqual(selected["engine"], "ollama")
        self.assertEqual(gen.call_args.args[1:3], ("qwen2.5:1.5b-instruct", ollama_client.DEFAULT_BASE_URL))
