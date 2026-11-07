"""검수 기록 생성과 JSON 내보내기: Streamlit과 분리된 순수 함수."""
from __future__ import annotations

import json
from typing import Any, Mapping


def make_review_record(
    *,
    review_id: str,
    decision: str,
    current_text: str,
    correction_text: str = "",
    audio_scope: str,
) -> dict[str, str]:
    if not review_id.strip():
        raise ValueError("검수 항목 ID가 필요합니다.")
    if decision == "수정 후 확정" and not correction_text.strip():
        raise ValueError("수정 후 확정을 선택한 경우 수정 내용을 입력해야 합니다.")
    return {
        "review_id": review_id,
        "audio_scope": audio_scope,
        "decision": decision,
        "original_text": current_text,
        "correction_text": correction_text.strip() if decision == "수정 후 확정" else "",
    }


def reviews_json(records: Mapping[str, Mapping[str, Any]]) -> bytes:
    payload = {"review_count": len(records), "reviews": [records[k] for k in sorted(records)]}
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
