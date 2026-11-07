from streamlit.testing.v1 import AppTest


def test_review_app_loads_and_records_decision():
    app = AppTest.from_file("app/review_app.py", default_timeout=30).run()
    assert not app.exception
    assert len(app.button) >= 1
    app.button[0].click().run()
    assert not app.exception
    assert len(app.session_state["reviews"]) == 1


def test_review_app_has_synthetic_source_label():
    app = AppTest.from_file("app/review_app.py", default_timeout=30).run()
    assert not app.exception
    assert any("합성" in c.value for c in app.caption)
