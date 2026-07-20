import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class CorsConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _find_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env["FRONTEND_ORIGINS"] = "https://optime-nursing.vercel.app/ , http://localhost:3000, http://127.0.0.1:3000"
        env["OPTIME_SMTP_STARTUP_TEST_ENABLED"] = "0"

        cls.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
            ],
            cwd=BACKEND_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                response = requests.get(f"{cls.base_url}/health", timeout=5)
                if response.status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(1)

        raise RuntimeError("Timed out waiting for backend test server to start.")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.wait(timeout=5)

    def _preflight(self, path: str, origin: str) -> requests.Response:
        return requests.options(
            f"{self.base_url}{path}",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=15,
        )

    def _get(self, path: str, origin: str) -> requests.Response:
        return requests.get(
            f"{self.base_url}{path}",
            headers={"Origin": origin},
            timeout=30,
        )

    def test_facilities_preflight_allows_vercel_origin(self) -> None:
        response = self._preflight("/facilities", "https://optime-nursing.vercel.app")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "https://optime-nursing.vercel.app")

    def test_governance_preflight_allows_vercel_origin(self) -> None:
        response = self._preflight("/governance/runtime-context", "https://optime-nursing.vercel.app")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "https://optime-nursing.vercel.app")

    def test_unknown_origin_is_not_granted(self) -> None:
        response = self._preflight("/facilities", "https://unknown.example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    def test_get_response_includes_allow_origin_for_vercel(self) -> None:
        response = self._get("/health", "https://optime-nursing.vercel.app")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "https://optime-nursing.vercel.app")


if __name__ == "__main__":
    unittest.main()