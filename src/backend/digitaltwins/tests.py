from unittest import mock

from django.test import SimpleTestCase, TestCase

from . import twins


class TwinFlattenTests(SimpleTestCase):
    def test_raw_strings_become_numbers(self):
        row = {"rowtime": "2026-10-08T03:25:00Z", "data": {"HUMIDITY": "57", "SURFACE_CURR_SPEED": ".3", "MMSI_NM": "등부표"}}
        flat = twins.flatten(row)
        self.assertEqual((flat["HUMIDITY"], flat["SURFACE_CURR_SPEED"], flat["MMSI_NM"]), (57, 0.3, "등부표"))

    def test_wrapped_source_measurements(self):
        row = {"data": {"id": "1", "status": "ok", "data": [
            {"pm10": 20, "logDateTime": "a", "date_time": "2026-10-08 10:00"},
            {"pm10": 30, "date_time": "2026-10-08 11:00"},
        ]}}
        self.assertEqual(twins.flatten(row)["pm10"], 30)  # 가장 최근 시각 값

    def test_parse_ref(self):
        self.assertEqual(twins.parse_ref("do:DT-1:DO-1"), ("do", "DT-1", "DO-1"))
        self.assertEqual(twins.latest_url("fdo:F:O"), "/api/twins/fdo/F/O/latest")
        with self.assertRaises(twins.TwinError):
            twins.parse_ref("x:1")


class TwinLinkageTests(SimpleTestCase):
    def test_counts_distinct_single_twins(self):
        index = {"DO-A": {"twinId": "DT-1", "twinName": "대기 트윈", "owner": "keti", "objectName": "대기"},
                 "DO-B": {"twinId": "DT-2", "twinName": "해양 트윈", "owner": "keti", "objectName": "해양"},
                 "DO-C": {"twinId": "DT-1", "twinName": "대기 트윈", "owner": "keti", "objectName": "대기2"}}
        entries = [{"ref": "fdo:F:O", "name": "통합 객체",
                    "members": [{"objectId": "DO-B", **index["DO-B"]}, {"objectId": "DO-C", **index["DO-C"]}]}]
        with mock.patch.object(twins, "catalog", return_value=(entries, index)):
            result = twins.linkage(["do:DT-1:DO-A", "fdo:F:O"])
        self.assertEqual(result["count"], 2)
        self.assertEqual({t["twinId"] for t in result["twins"]}, {"DT-1", "DT-2"})
        self.assertEqual(result["twins"][0]["sources"], ["Digital Connector", "Digital Brain"])

    def test_metadata_store_refs_and_connector_outage(self):
        meta = {"DT-1": {"twinName": "대기 트윈", "owner": "keti"}, "DT-3": {"twinName": "침수 트윈", "owner": "포항시"}}
        # Connector 목록을 받지 못한 상태(빈 카탈로그)에서도 2세부 저장소 메타정보로 센다.
        with mock.patch.object(twins, "catalog", return_value=([], {})), \
             mock.patch.object(twins, "_metadata_twins", return_value=meta):
            result = twins.linkage(["meta:DT-3", "do:DT-1:DO-A", "meta:DT-1", "meta:NONE"],
                                   {"meta:DT-3": "침수 트윈 메타정보"})
        self.assertEqual(result["count"], 2)
        by_id = {t["twinId"]: t for t in result["twins"]}
        self.assertEqual(by_id["DT-3"]["via"], ["침수 트윈 메타정보"])
        self.assertEqual(by_id["DT-1"]["twinName"], "대기 트윈")
        self.assertEqual(by_id["DT-1"]["sources"], ["2세부 메타데이터 저장소"])
        self.assertEqual(result["unresolved"], ["meta:NONE"])


def _resp(status=200, body=None):
    r = mock.Mock()
    r.status_code = status
    r.ok = status < 400
    r.json.return_value = body if body is not None else {"data": []}
    r.text = ""
    return r


class IntegrationCallLogTests(SimpleTestCase):
    """메타정보를 어디서 조회했는지 운영 로그(slct.integration)로 남는지."""

    def test_connector_call_is_logged_with_url_and_count(self):
        body = {"data": [{"digital_object_id": "DO-1"}, {"digital_object_id": "DO-2"}]}
        with mock.patch("requests.get", return_value=_resp(200, body)), \
             self.assertLogs("slct.integration", "INFO") as logs:
            twins.digital_objects("KR-01-O84213-20260002")
        line = logs.output[0]
        self.assertIn("Digital Connector GET", line)
        self.assertIn("/fedit/v1/digital-twins/KR-01-O84213-20260002/digital-objects", line)
        self.assertIn("→ 200 (2건", line)

    def test_failure_is_warning(self):
        with mock.patch("requests.get", return_value=_resp(503)), \
             self.assertLogs("slct.integration", "WARNING") as logs:
            with self.assertRaises(twins.TwinError):
                twins.digital_twins()
        self.assertIn("실패: HTTP 503", logs.output[0])

    def test_brain_call_is_logged(self):
        with mock.patch("requests.request", return_value=_resp(200, [{"federated_digital_twin_id": "F"}])), \
             self.assertLogs("slct.integration", "INFO") as logs:
            from . import brain
            brain.federated_twins()
        self.assertIn("Digital Brain GET", logs.output[0])
        self.assertIn("/fedit/v1/federated-twins", logs.output[0])

    def test_metadata_store_call_hides_token(self):
        from . import fedit_client
        with mock.patch.dict("os.environ", {"FEDIT_META_TOKEN": "secret-token-value"}), \
             mock.patch("requests.get", return_value=_resp(200, {"data": [{"id": 1}]})), \
             self.assertLogs("slct.integration", "INFO") as logs:
            fedit_client.list_resource("digitalTwins")
        joined = "\n".join(logs.output)
        self.assertIn("2세부 메타데이터 저장소 GET", joined)
        self.assertIn("/meta/api/v1/resource/digitalTwins", joined)
        self.assertNotIn("secret-token-value", joined)

    def test_catalog_refresh_logs_one_summary_including_worker_calls(self):
        dts = {"data": [{"digital_twin_id": "DT-1", "digital_twin_name": "대기"}]}
        dos = {"data": [{"digital_object_id": f"DO-{i}", "digital_object_name": f"객체{i}"} for i in range(3)]}
        rows = {"data": [{"rowtime": "2026-10-12T00:00:00Z", "data": {"pm10": 20}}]}

        def fake_get(url, params=None, timeout=None):
            if url.endswith("/digital-twins"):
                return _resp(200, dts)
            if url.endswith("/digital-objects"):
                return _resp(200, dos)
            return _resp(200, rows)

        with mock.patch("requests.get", side_effect=fake_get), \
             mock.patch.object(twins.brain, "federated_twins", return_value=[]), \
             self.assertLogs("slct.integration", "INFO") as logs:
            entries, _ = twins.catalog(refresh=True)
        self.assertEqual(len(entries), 3)
        info = [line for line in logs.output if line.startswith("INFO")]
        self.assertEqual(len(info), 1, info)  # 줄마다의 기록은 DEBUG, 요약 한 줄만 INFO
        self.assertIn("트윈 목록 갱신: 호출 5건, 실패 0건", info[0])  # 목록 1 + 객체 1 + 데이터 3(작업 스레드)

    def test_refs_in_xml_matches_editor_rule(self):
        xml = """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:pipeline="pipeline://">
          <bpmn:process id="P">
            <bpmn:serviceTask id="A"><bpmn:extensionElements><pipeline:parameters>
              <pipeline:parameter name="a" url="/api/twins/do/DT-1/DO-1/latest" twin="do:DT-1:DO-1"/></pipeline:parameters></bpmn:extensionElements></bpmn:serviceTask>
            <bpmn:serviceTask id="B"><bpmn:extensionElements><pipeline:parameters>
              <pipeline:parameter name="b" url="/api/twins/do/DT-2/DO-9/latest"/></pipeline:parameters></bpmn:extensionElements></bpmn:serviceTask>
            <bpmn:serviceTask id="C"><bpmn:extensionElements><pipeline:parameters>
              <pipeline:parameter name="c" url="/api/fedit/objects/latest?fdt=F&amp;fdo=O"/></pipeline:parameters></bpmn:extensionElements></bpmn:serviceTask>
            <bpmn:serviceTask id="D"><bpmn:extensionElements><pipeline:parameters>
              <pipeline:parameter name="d" url="/api/pipelines/run?id=notify.sms"/></pipeline:parameters></bpmn:extensionElements></bpmn:serviceTask>
            <bpmn:serviceTask id="M" name="침수 트윈 메타정보"><bpmn:extensionElements><pipeline:parameters>
              <pipeline:parameter name="m" url="/api/fedit/metadata/digitalTwins" method="GET"/>
              <pipeline:input name="digitalTwinId" value="KR-02-1"/></pipeline:parameters></bpmn:extensionElements></bpmn:serviceTask>
            <bpmn:serviceTask id="N" name="입력으로 받는 메타정보"><bpmn:extensionElements><pipeline:parameters>
              <pipeline:parameter name="n" url="/api/fedit/metadata/digitalTwins" method="GET"/>
              <pipeline:input name="digitalTwinId" source="입력값"/></pipeline:parameters></bpmn:extensionElements></bpmn:serviceTask>
          </bpmn:process></bpmn:definitions>"""
        self.assertEqual(twins.refs_in_xml(xml), ["do:DT-1:DO-1", "do:DT-2:DO-9", "fdo:F:O", "meta:KR-02-1"])
        refs, labels = twins.refs_in_xml(xml, with_labels=True)
        self.assertEqual(labels["meta:KR-02-1"], "침수 트윈 메타정보")
        self.assertEqual(twins.refs_in_xml("<not xml"), [])


class TwinLinkageApiTests(TestCase):
    def test_diagram_param_reads_saved_logic(self):
        from bpmns.models import BpmnDiagram

        xml = """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:pipeline="pipeline://">
          <bpmn:process id="P"><bpmn:serviceTask id="M" name="침수 트윈 메타정보"><bpmn:extensionElements><pipeline:parameters>
            <pipeline:parameter name="m" url="/api/fedit/metadata/digitalTwins"/><pipeline:input name="digitalTwinId" value="DT-3"/>
          </pipeline:parameters></bpmn:extensionElements></bpmn:serviceTask></bpmn:process></bpmn:definitions>"""
        BpmnDiagram.objects.create(uid="lk", xml=xml)
        meta = {"DT-3": {"twinName": "침수 트윈", "owner": "포항시"}}
        with mock.patch.object(twins, "catalog", return_value=([], {})), \
             mock.patch.object(twins, "_metadata_twins", return_value=meta):
            resp = self.client.get("/api/twins/linkage", {"diagram": "lk"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual((data["count"], data["diagram"]), (1, "lk"))
        self.assertEqual(data["twins"][0]["via"], ["침수 트윈 메타정보"])
        self.assertEqual(self.client.get("/api/twins/linkage", {"diagram": "none"}).status_code, 404)
