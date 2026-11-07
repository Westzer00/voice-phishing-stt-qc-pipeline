import pytest
from src.speaker_alignment import align_words, best_speaker_for_word


def test_overlap_wins():
    diar = [
        {"start": 0.0, "end": 1.0, "speaker": "A"},
        {"start": 0.8, "end": 2.0, "speaker": "B"},
    ]
    speaker, overlap = best_speaker_for_word(0.9, 1.4, diar)
    assert speaker == "B"
    assert overlap > 0.0


def test_turn_split_on_speaker_change():
    asr = {
        "segments": [
            {
                "words": [
                    {"start": 0.1, "end": 0.5, "word": "안녕 ", "probability": 0.9},
                    {"start": 0.6, "end": 1.0, "word": "하세요", "probability": 0.9},
                    {"start": 1.2, "end": 1.5, "word": "네", "probability": 0.9},
                ]
            }
        ]
    }
    diar = [
        {"start": 0.0, "end": 1.05, "speaker": "A"},
        {"start": 1.1, "end": 2.0, "speaker": "B"},
    ]
    _, turns = align_words(asr, diar)
    assert [turn["speaker"] for turn in turns] == ["A", "B"]


def test_nearest_speaker_fallback_and_unknown():
    intervals = [{"start": 1.0, "end": 2.0, "speaker": "A"}]
    assert best_speaker_for_word(2.1, 2.3, intervals, fallback_sec=0.5)[0] == "A"
    assert best_speaker_for_word(5.0, 5.3, intervals, fallback_sec=0.5)[0] == "UNKNOWN"


def test_time_gap_starts_new_turn_for_same_speaker():
    data = {"segments": [{"words": [
        {"start": 0.0, "end": 0.2, "word": "안녕 "},
        {"start": 1.9, "end": 2.1, "word": "다시"},
    ]}]}
    words, turns = align_words(data, [{"start": 0, "end": 4, "speaker": "A"}])
    assert len(words) == 2
    assert len(turns) == 2
    assert turns[0]["speaker"] == turns[1]["speaker"] == "A"

@pytest.mark.parametrize("start,end", [
    (-0.1, 1.0),
    (2.0, 1.0),
    (float("nan"), 1.0),
    (0.0, float("inf")),
])
def test_invalid_word_timestamps_raise_instead_of_silent_alignment(start, end):
    diar = [{"start": 0.0, "end": 2.0, "speaker": "A"}]
    with pytest.raises(ValueError, match="Invalid ASR word interval"):
        best_speaker_for_word(start, end, diar)
    with pytest.raises(ValueError, match="Invalid ASR word interval"):
        align_words({"segments": [{"words": [
            {"start": start, "end": end, "word": "test"}
        ]}]}, diar)
