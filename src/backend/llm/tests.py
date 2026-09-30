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
