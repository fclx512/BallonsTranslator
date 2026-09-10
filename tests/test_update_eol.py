"""Delta updates must not deliver LF-only batch files.

``raw.githubusercontent.com`` serves the stored git blob, and ``text`` files are
normalised to LF on commit -- ``eol=crlf`` in ``.gitattributes`` only affects
checkout and archive output.  ``cmd.exe`` cannot parse an LF-only ``.bat``
(it loses sync and aborts the whole script), so a manifest-delta update would
silently brick the launcher of every ZIP-mode install.
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_check_update():
    spec = importlib.util.spec_from_file_location(
        "check_update_under_test", ROOT / "scripts" / "check_update.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDeltaUpdateLineEndings(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

        self.mod = _load_check_update()
        self.mod._update_dir = lambda: self.root / "_update"
        self.mod._read_local_manifest = lambda: {
            "files": {"launch.bat": "sha256:old", "ui/mainwindow.py": "sha256:old"}
        }

        self.served = {}

        def fake_http_get(url):
            for name, payload in self.served.items():
                if url.endswith(name):
                    return payload, {}
            raise AssertionError(f"unexpected url: {url}")

        self.mod._http_get = fake_http_get
        self.mod._update_dir().mkdir(parents=True, exist_ok=True)

    def _serve(self, **files):
        self.served["manifest.json"] = json.dumps(
            {"files": {name: "sha256:new" for name in files}}
        ).encode("utf-8")
        for name, payload in files.items():
            self.served[name] = payload

    def test_bat_lands_as_crlf_while_py_is_untouched(self):
        self._serve(
            **{
                "launch.bat": b"@echo off\nsetlocal\n",
                "ui/mainwindow.py": b"import os\nprint(os)\n",
            }
        )

        self.assertTrue(self.mod._download_manifest_update("deadbeef"))

        files = self.mod._update_dir() / "files"
        self.assertEqual(
            (files / "launch.bat").read_bytes(), b"@echo off\r\nsetlocal\r\n"
        )
        self.assertEqual(
            (files / "ui/mainwindow.py").read_bytes(), b"import os\nprint(os)\n"
        )

    def test_as_crlf_is_idempotent_and_suffix_scoped(self):
        as_crlf = self.mod._as_crlf
        self.assertEqual(as_crlf("a.bat", b"x\r\ny\r\n"), b"x\r\ny\r\n")
        self.assertEqual(as_crlf("A.BAT", b"x\ny"), b"x\r\ny")
        self.assertEqual(as_crlf("scripts/run.cmd", b"x\ny"), b"x\r\ny")
        self.assertEqual(as_crlf("ui/mainwindow.py", b"x\ny"), b"x\ny")


if __name__ == "__main__":
    unittest.main()
