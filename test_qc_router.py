from src.qc_router import QCRules, flags_for_segment, route_segments


def test_critical_low_confidence_is_routed():
    segment = {
        "start": 1.0,
        "end": 3.0,
        "text": "계좌번호를 확인하겠습니다",
        "avg_logprob": -0.4,
        "compression_ratio": 1.2,
        "no_speech_prob": 0.01,
        "words": [
            {"word": "계좌번호", "probability": 0.40},
            {"word": "확인", "probability": 0.50},
        ],
    }
    flags = flags_for_segment(segment, repeated=False, rules=QCRules())
    assert "CRITICAL_TERM_LOWCONF" in flags
    assert "LOW_WORD_CONF" in flags


def test_route_merges_nearby_suspicious_segments():
    asr = {
        "duration_sec": 30,
        "segments": [
            {"id": 1, "start": 5, "end": 7, "text": "금액 백만원", "avg_logprob": -0.9, "words": []},
            {"id": 2, "start": 8, "end": 10, "text": "계좌 확인", "avg_logprob": -0.9, "words": []},
        ],
    }
    spans = route_segments(asr)
    assert len(spans) == 1
    assert spans[0]["segment_ids"] == [1, 2]
