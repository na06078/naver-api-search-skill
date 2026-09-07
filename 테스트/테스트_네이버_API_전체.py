# 테스트_네이버_API_전체.py
"""네이버 API 호출기 오프라인 단위 테스트 (PRD 13장).

표준 라이브러리 unittest만 사용한다. 네트워크와 실제 API 키가 필요 없다.
가짜 HttpTransport를 주입해 CLI 통합까지 검증한다.

실행:
    python -m unittest 테스트_네이버_API_전체 -v
또는:
    python "테스트_네이버_API_전체.py"
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 호출기 모듈 경로를 sys.path에 추가한다.
_HERE = Path(__file__).resolve().parent
_CALLER_DIR = _HERE.parent / "호출기"
sys.path.insert(0, str(_CALLER_DIR))

import 네이버_API_계약 as 계약  # noqa: E402
import 네이버_API_검증 as 검증  # noqa: E402
import 네이버_API_설정 as 설정  # noqa: E402
import 네이버_API_오류 as 오류  # noqa: E402
import 네이버_API_전송 as 전송  # noqa: E402
import 네이버_API_정규화 as 정규화  # noqa: E402
import 네이버_API_호출기 as 호출기  # noqa: E402

_FIXTURES = _HERE / "테스트_응답_자료"


def load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


class FakeTransport:
    """요청을 기록하고 미리 정한 응답을 돌려주는 가짜 전송."""

    def __init__(self, status: int = 200, body: bytes = b"{}") -> None:
        self.status = status
        self.body = body
        self.calls: list[dict] = []

    def request(self, method, url, headers, body, timeout_seconds):
        self.calls.append(
            {"method": method, "url": url, "headers": dict(headers), "body": body}
        )
        return 전송.HttpResponse(self.status, {}, self.body)


class 설정테스트(unittest.TestCase):
    def setUp(self):
        self._saved = {
            k: os.environ.pop(k, None)
            for k in (설정.ENV_CLIENT_ID, 설정.ENV_CLIENT_SECRET)
        }

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_env_file_load(self):
        d = Path(tempfile.mkdtemp())
        f = d / ".env"
        f.write_text(
            "# c\nNAVER_CLIENT_ID=id1\nexport NAVER_CLIENT_SECRET=\"sec1\"\n",
            encoding="utf-8",
        )
        cred = 설정.load_credentials(f)
        self.assertEqual(cred.client_id, "id1")
        self.assertEqual(cred.client_secret, "sec1")

    def test_secret_not_in_repr(self):
        cred = 설정.NaverCredentials("id1", "TOPSECRET")
        self.assertNotIn("TOPSECRET", repr(cred))
        self.assertNotIn("TOPSECRET", str(cred))

    def test_missing_raises(self):
        d = Path(tempfile.mkdtemp())
        f = d / ".env"
        f.write_text("NAVER_CLIENT_ID=only\n", encoding="utf-8")
        with self.assertRaises(설정.ConfigError) as ctx:
            설정.load_credentials(f)
        self.assertEqual(ctx.exception.code, "E_CONFIG_MISSING")

    def test_env_overrides_file(self):
        d = Path(tempfile.mkdtemp())
        f = d / ".env"
        f.write_text("NAVER_CLIENT_ID=fileid\nNAVER_CLIENT_SECRET=filesec\n", encoding="utf-8")
        os.environ["NAVER_CLIENT_ID"] = "envid"
        os.environ["NAVER_CLIENT_SECRET"] = "envsec"
        cred = 설정.load_credentials(f)
        self.assertEqual(cred.client_id, "envid")


class 검색검증테스트(unittest.TestCase):
    SK = 계약.SearchKind

    def _bad(self, code, req):
        with self.assertRaises(오류.CallerError) as ctx:
            검증.validate_search(req)
        self.assertEqual(ctx.exception.code, code)

    def test_empty_query(self):
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.NEWS, query="  "))

    def test_display_range(self):
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.NEWS, query="x", display=101))
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.NEWS, query="x", display=0))

    def test_local_limits(self):
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.LOCAL, query="x", display=6))
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.LOCAL, query="x", start=2))
        검증.validate_search(계약.SearchRequest(kind=self.SK.LOCAL, query="x", display=5, start=1))

    def test_web_no_sort(self):
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.WEB, query="x", sort="date"))

    def test_sort_value(self):
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.BLOG, query="x", sort="point"))
        검증.validate_search(계약.SearchRequest(kind=self.SK.KIN, query="x", sort="point"))

    def test_filter_image_only(self):
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.BLOG, query="x", image_filter="large"))
        self._bad("E_ARG_INVALID", 계약.SearchRequest(kind=self.SK.IMAGE, query="x", image_filter="huge"))
        검증.validate_search(계약.SearchRequest(kind=self.SK.IMAGE, query="x", image_filter="large"))


class 트렌드검증테스트(unittest.TestCase):
    G = 계약.KeywordGroup

    def _bad(self, req):
        with self.assertRaises(오류.CallerError) as ctx:
            검증.validate_trend(req)
        self.assertEqual(ctx.exception.code, "E_SCHEMA_INVALID")

    def test_ok(self):
        검증.validate_trend(
            계약.TrendRequest("2026-01-01", "2026-03-01", "month", (self.G("LTX", ("LTX",)),))
        )

    def test_bad_date(self):
        self._bad(계약.TrendRequest("2026-13-01", "2026-03-01", "month", (self.G("a", ("a",)),)))

    def test_reverse_date(self):
        self._bad(계약.TrendRequest("2026-03-01", "2026-01-01", "month", (self.G("a", ("a",)),)))

    def test_before_min_date(self):
        self._bad(계약.TrendRequest("2015-01-01", "2026-01-01", "month", (self.G("a", ("a",)),)))

    def test_too_many_groups(self):
        self._bad(
            계약.TrendRequest(
                "2026-01-01", "2026-03-01", "month",
                tuple(self.G(f"g{i}", ("k",)) for i in range(6)),
            )
        )

    def test_too_many_keywords(self):
        self._bad(
            계약.TrendRequest(
                "2026-01-01", "2026-03-01", "month",
                (self.G("a", tuple(str(i) for i in range(21))),),
            )
        )


class 쇼핑검증테스트(unittest.TestCase):
    SM = 계약.ShoppingMode

    def test_categories_ok(self):
        검증.validate_shopping(
            계약.ShoppingRequest(
                self.SM.CATEGORIES, "2026-01-01", "2026-03-01", "month",
                categories=(("패션", "50000000"),),
            )
        )

    def test_categories_too_many(self):
        with self.assertRaises(오류.CallerError):
            검증.validate_shopping(
                계약.ShoppingRequest(
                    self.SM.CATEGORIES, "2026-01-01", "2026-03-01", "month",
                    categories=tuple((f"n{i}", str(i)) for i in range(4)),
                )
            )

    def test_category_device_needs_code(self):
        with self.assertRaises(오류.CallerError) as ctx:
            검증.validate_shopping(
                계약.ShoppingRequest(self.SM.CATEGORY_DEVICE, "2026-01-01", "2026-03-01", "month")
            )
        self.assertEqual(ctx.exception.code, "E_ARG_INVALID")

    def test_keyword_single(self):
        with self.assertRaises(오류.CallerError):
            검증.validate_shopping(
                계약.ShoppingRequest(
                    self.SM.CATEGORY_KEYWORD_DEVICE, "2026-01-01", "2026-03-01", "month",
                    category_code="50000000", keywords=(("a", "a"), ("b", "b")),
                )
            )


class 정규화테스트(unittest.TestCase):
    SK = 계약.SearchKind

    def test_strip_highlight(self):
        self.assertEqual(정규화.strip_highlight("<b>x</b> &amp; y"), "x & y")
        self.assertEqual(정규화.strip_highlight(None), "")

    def test_blog_fixture(self):
        raw = load_fixture("블로그_응답.json")
        out = 정규화.normalize_search_response(
            self.SK.BLOG, 계약.SearchRequest(kind=self.SK.BLOG, query="AMD"), raw
        )
        it = out["response"]["items"][0]
        self.assertEqual(it["title"], "AMD ComfyUI 설치 후기")
        self.assertEqual(it["source_name"], "테크블로그")
        self.assertEqual(it["published_at"], "20260901")
        self.assertNotIn("<b>", json.dumps(out, ensure_ascii=False))

    def test_image_fixture(self):
        raw = load_fixture("이미지_응답.json")
        out = 정규화.normalize_search_response(
            self.SK.IMAGE, 계약.SearchRequest(kind=self.SK.IMAGE, query="원룸"), raw
        )
        it = out["response"]["items"][0]
        self.assertEqual(it["thumbnail_url"], "https://image.example.com/a_thumb.jpg")
        self.assertEqual(it["metadata"]["size_width"], "1200")

    def test_local_fixture(self):
        raw = load_fixture("지역_응답.json")
        out = 정규화.normalize_search_response(
            self.SK.LOCAL, 계약.SearchRequest(kind=self.SK.LOCAL, query="죽", display=5), raw
        )
        m = out["response"]["items"][0]["metadata"]
        self.assertEqual(m["road_address"], "서울특별시 강남구 테헤란로 100")

    def test_news_fixture_url_split(self):
        raw = load_fixture("뉴스_응답.json")
        out = 정규화.normalize_search_response(
            self.SK.NEWS, 계약.SearchRequest(kind=self.SK.NEWS, query="LTX", sort="date"), raw
        )
        it = out["response"]["items"][0]
        self.assertEqual(it["url"], "https://n.news.naver.com/article/001/0001")
        self.assertEqual(it["source_url"], "https://press.example.com/article/1")

    def test_trend_fixture(self):
        raw = load_fixture("검색어트렌드_응답.json")
        out = 정규화.normalize_datalab_response("search_trend", {}, raw)
        s = out["response"]["series"][0]
        self.assertEqual(s["label"], "LTX")
        self.assertEqual(s["keywords"], ["LTX", "LTX Video"])
        self.assertIsNone(s["data"][0]["group"])

    def test_shopping_fixture(self):
        raw = load_fixture("쇼핑인사이트_응답.json")
        out = 정규화.normalize_datalab_response("shopping_insight", {}, raw)
        s = out["response"]["series"][0]
        self.assertEqual(s["keywords"], ["정장"])
        self.assertEqual(s["data"][0]["group"], "mo")


class 오류테스트(unittest.TestCase):
    def test_status_mapping(self):
        self.assertEqual(오류.http_status_to_error(403).code, "E_API_PERMISSION")
        self.assertEqual(오류.http_status_to_error(401).code, "E_API_AUTH")
        self.assertEqual(오류.http_status_to_error(400).code, "E_API_BAD_REQUEST")
        self.assertEqual(오류.http_status_to_error(429).code, "E_API_RATE_LIMIT")
        self.assertEqual(오류.http_status_to_error(503).code, "E_API_SERVER")

    def test_envelope_no_secret_slot(self):
        e = 오류.CallerError("E_API_PERMISSION", "권한 없음", http_status=403)
        env = 오류.error_envelope("search", "blog", e)
        self.assertFalse(env["ok"])
        self.assertNotIn("client_secret", json.dumps(env).lower())


class 전송테스트(unittest.TestCase):
    def test_whitelist(self):
        전송.assert_allowed_url("https://naverapihub.apigw.ntruss.com/search/v1/blog")
        for bad in ["http://naverapihub.apigw.ntruss.com/x", "https://evil.com/x",
                    "https://openapi.naver.com/x",
                    "https://naverapihub.apigw.ntruss.com.evil.com/x"]:
            with self.assertRaises(오류.CallerError):
                전송.assert_allowed_url(bad)

    def test_parse_json(self):
        r = 전송.HttpResponse(200, {}, b'{"total": 3}')
        self.assertEqual(전송.parse_json_body(r)["total"], 3)
        for bad in [b"nope", b"[1,2]", b"\xff"]:
            with self.assertRaises(오류.CallerError):
                전송.parse_json_body(전송.HttpResponse(200, {}, bad))


class CLI통합테스트(unittest.TestCase):
    def setUp(self):
        os.environ["NAVER_CLIENT_ID"] = "id"
        os.environ["NAVER_CLIENT_SECRET"] = "SECRETXYZ"

    def tearDown(self):
        os.environ.pop("NAVER_CLIENT_ID", None)
        os.environ.pop("NAVER_CLIENT_SECRET", None)

    def test_search_success(self):
        ft = FakeTransport(200, json.dumps(load_fixture("뉴스_응답.json")).encode())
        out, code = 호출기.run(
            ["search", "--type", "news", "--query", "LTX", "--sort", "date"], transport=ft
        )
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])
        self.assertEqual(ft.calls[0]["method"], "GET")
        self.assertIn("sort=date", ft.calls[0]["url"])
        self.assertEqual(ft.calls[0]["headers"]["X-NCP-APIGW-API-KEY-ID"], "id")

    def test_trend_post(self):
        ft = FakeTransport(200, json.dumps(load_fixture("검색어트렌드_응답.json")).encode())
        out, code = 호출기.run(
            ["trend", "--start-date", "2026-01-01", "--end-date", "2026-03-01",
             "--time-unit", "month", "--group", "LTX=LTX,LTX Video"],
            transport=ft,
        )
        self.assertEqual(code, 0)
        self.assertEqual(ft.calls[0]["method"], "POST")
        body = json.loads(ft.calls[0]["body"].decode())
        self.assertEqual(body["keywordGroups"][0]["keywords"], ["LTX", "LTX Video"])

    def test_validation_exit_code(self):
        out, code = 호출기.run(
            ["search", "--type", "web", "--query", "x", "--sort", "date"],
            transport=FakeTransport(),
        )
        self.assertEqual(code, 2)
        self.assertEqual(out["error"]["code"], "E_ARG_INVALID")

    def test_permission_exit_code(self):
        out, code = 호출기.run(
            ["search", "--type", "blog", "--query", "x"],
            transport=FakeTransport(403, b"{}"),
        )
        self.assertEqual(code, 4)
        self.assertEqual(out["error"]["code"], "E_API_PERMISSION")

    def test_no_secret_in_error(self):
        out, _ = 호출기.run(
            ["search", "--type", "blog", "--query", "x"],
            transport=FakeTransport(500, b"{}"),
        )
        self.assertNotIn("SECRETXYZ", json.dumps(out, ensure_ascii=False))

    def test_help_no_secret(self):
        out, code = 호출기.run(["help"], transport=FakeTransport())
        self.assertEqual(code, 0)
        self.assertNotIn("SECRETXYZ", json.dumps(out, ensure_ascii=False))
        self.assertEqual(len(out["response"]["shopping_modes"]), 8)

    def test_missing_credentials(self):
        os.environ.pop("NAVER_CLIENT_ID", None)
        os.environ.pop("NAVER_CLIENT_SECRET", None)
        out, code = 호출기.run(
            ["search", "--type", "blog", "--query", "x"], transport=FakeTransport()
        )
        self.assertEqual(code, 3)
        self.assertEqual(out["error"]["code"], "E_CONFIG_MISSING")


if __name__ == "__main__":
    unittest.main(verbosity=2)
