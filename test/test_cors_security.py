#!/usr/bin/env python3
"""
Test Suite CORS Security (Stage 3B.4.3)
Kiểm thử HTTP thực tế các yêu cầu OPTIONS, GET, POST từ origin hợp lệ và không hợp lệ.
"""
import unittest
import urllib.request
import urllib.error
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BACKEND_URL = "http://localhost:8000"

class TestCorsSecurity(unittest.TestCase):
    def _send_request(self, method, path, origin=None, headers=None, data=None):
        url = f"{BACKEND_URL}{path}"
        req_headers = {}
        if headers:
            req_headers.update(headers)
        if origin is not None:
            req_headers["Origin"] = origin
        body = json.dumps(data).encode("utf-8") if data is not None else None
        if data is not None and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"
            
        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp_headers = dict(resp.headers)
                return resp.status, resp_headers, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            resp_headers = dict(e.headers)
            return e.code, resp_headers, e.read().decode("utf-8")

    def test_01_allowed_origin_get_receives_cors_header(self):
        """Origin trong whitelist (http://localhost:3000) nhận được Access-Control-Allow-Origin tương ứng."""
        status, headers, body = self._send_request("GET", "/api/status", origin="http://localhost:3000")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "http://localhost:3000")
        self.assertEqual(headers.get("Access-Control-Max-Age"), "86400")

    def test_02_disallowed_origin_get_receives_no_cors_header(self):
        """Origin độc hại / không thuộc whitelist KHÔNG nhận được header Access-Control-Allow-Origin."""
        status, headers, body = self._send_request("GET", "/api/status", origin="http://malicious-site.com")
        self.assertEqual(status, 200)
        self.assertNotIn("Access-Control-Allow-Origin", headers, 
                         "Backend tuyệt đối không phát Access-Control-Allow-Origin cho origin không hợp lệ")

    def test_03_allowed_origin_options_preflight(self):
        """OPTIONS preflight từ allowed origin trả về 200 và đầy đủ headers CORS + Max-Age."""
        headers_req = {
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
        status, headers, body = self._send_request("OPTIONS", "/api/auth/login", origin="http://127.0.0.1:5500", headers=headers_req)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5500")
        self.assertIn("POST", headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("Authorization", headers.get("Access-Control-Allow-Headers", ""))
        self.assertEqual(headers.get("Access-Control-Max-Age"), "86400")

    def test_04_disallowed_origin_options_preflight(self):
        """OPTIONS preflight từ origin không hợp lệ KHÔNG nhận được Access-Control-Allow-Origin."""
        headers_req = {
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
        status, headers, body = self._send_request("OPTIONS", "/api/auth/login", origin="https://evil-attacker.io", headers=headers_req)
        self.assertEqual(status, 200)
        self.assertNotIn("Access-Control-Allow-Origin", headers, 
                         "Preflight từ origin ngoài whitelist không được phép chứa CORS header")

    def test_05_allowed_origin_post(self):
        """POST request từ allowed origin nhận được Access-Control-Allow-Origin."""
        status, headers, body = self._send_request("POST", "/api/auth/login", origin="http://localhost:5173", data={"address": "0x123", "nonce": "abc", "signature": "0x456"})
        # Chữ ký sai hoặc nonce sai trả về 400 hoặc 401 nhưng header CORS vẫn phải khớp origin
        self.assertIn(status, [400, 401])
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "http://localhost:5173")

    def test_06_disallowed_origin_post(self):
        """POST request từ disallowed origin KHÔNG nhận được Access-Control-Allow-Origin."""
        status, headers, body = self._send_request("POST", "/api/auth/login", origin="http://attacker-c2.com", data={"address": "0x123", "nonce": "abc", "signature": "0x456"})
        self.assertNotIn("Access-Control-Allow-Origin", headers)

if __name__ == "__main__":
    unittest.main()
