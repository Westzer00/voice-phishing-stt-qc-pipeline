import json
import pytest
from src.review_records import make_review_record, reviews_json


def test_save_decision_and_correction():
    record = make_review_record(
        review_id="r1", audio_scope="LOCAL",
        current_text="은행권", decision="수정 후 확정", correction_text="은행",
    )
    assert record["decision"] == "수정 후 확정"
    assert record["correction_text"] == "은행"


def test_correction_required_for_fix():
    with pytest.raises(ValueError, match="수정 내용"):
        make_review_record(
            review_id="r2", audio_scope="FULL",
            current_text="잘못된 문장", decision="수정 후 확정", correction_text=" ",
        )


def test_export_record_is_utf8_and_stable():
    r1 = make_review_record(
        review_id="r2", audio_scope="LOCAL",
        current_text="기존", decision="현재 STT 그대로 확정",
    )
    r2 = make_review_record(
        review_id="r1", audio_scope="FULL",
        current_text="삭제할 문장", decision="음성에 없는 문장 삭제",
    )
    parsed = json.loads(reviews_json({"r2": r1, "r1": r2}).decode("utf-8"))
    assert parsed["review_count"] == 2
    assert parsed["reviews"][0]["review_id"] == "r1"
    assert parsed["reviews"][1]["review_id"] == "r2"
