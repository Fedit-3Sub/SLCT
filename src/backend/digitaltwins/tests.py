from unittest import mock

from django.test import SimpleTestCase

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
