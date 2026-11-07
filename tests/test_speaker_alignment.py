from speaker_alignment import align_words, best_speaker_for_word


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
