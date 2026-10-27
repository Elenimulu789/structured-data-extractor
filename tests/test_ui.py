"""End-to-end Streamlit widget tests using the real offline pipeline."""
from streamlit.testing.v1 import AppTest
from pathlib import Path
APP = Path(__file__).resolve().parents[1] / "src" / "app.py"


def test_ui_extract_and_reflection():
    app = AppTest.from_file(APP, default_timeout=10).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert any("RECONCILED" in message.value for message in app.success)
    app.button[1].click().run()
    assert not app.exception
    assert any("REPAIRED_VIA_REFLECTION" in caption.value for caption in app.caption)


def test_ui_hard_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("DLQ_DIR", str(tmp_path))
    app = AppTest.from_file(APP, default_timeout=10).run()
    app.button[2].click().run(timeout=10)
    assert not app.exception
    assert any("No valid record" in err.value for err in app.error)
    assert len(list(tmp_path.glob("*.json"))) == 1
