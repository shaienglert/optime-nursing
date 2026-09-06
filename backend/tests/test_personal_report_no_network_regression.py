from pathlib import Path


def test_report_service_files_do_not_gain_network_calls():
    root = Path(__file__).parents[1] / "app" / "services"
    text = "\n".join((root / name).read_text().lower() for name in ["personal_decision_report_builder.py", "personal_decision_report_renderer.py"])
    for forbidden in ("requests.get", "requests.post", "httpx.get", "httpx.post", "urllib.request"):
        assert forbidden not in text
