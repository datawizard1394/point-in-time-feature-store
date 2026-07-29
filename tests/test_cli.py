import json
import tempfile
import unittest
from pathlib import Path

from feature_store.cli import main


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_demo_writes_all_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            status = main(
                [
                    "demo",
                    "--transactions",
                    str(ROOT / "data/transactions.csv"),
                    "--observations",
                    str(ROOT / "data/observations.csv"),
                    "--as-of",
                    "2026-07-28T12:00:00Z",
                    "--output-dir",
                    str(output),
                ]
            )
            self.assertEqual(status, 0)
            summary = json.loads(
                (output / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(summary["offline_rows"], 4)
            self.assertTrue((output / "offline-features.csv").exists())
            self.assertTrue((output / "online-snapshot.json").exists())
            self.assertTrue((output / "parity-report.json").exists())
            self.assertTrue((output / "freshness-report.json").exists())


if __name__ == "__main__":
    unittest.main()
