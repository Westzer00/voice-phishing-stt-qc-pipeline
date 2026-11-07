"""Synthetic RTTM interval validation: GPU inference and private audio not used."""
import pytest
from src.nemo_diarization import parse_rttm


@pytest.mark.parametrize("start,duration", [
    ("-1", "1"),
    ("0", "0"),
    ("0", "-0.1"),
    ("NaN", "1"),
    ("0", "inf"),
    ("inf", "1"),
    ("1e309", "1"),
    ("oops", "1"),
])
def test_reject_invalid_rttm_times(tmp_path, start, duration):
    file = tmp_path / "invalid.rttm"
    file.write_text(
        f"SPEAKER dummy 1 {start} {duration} <NA> <NA> spkA <NA> <NA>\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid RTTM"):
        parse_rttm(file)


def test_valid_rttm_boundary_segments_are_sorted(tmp_path):
    file = tmp_path / "valid.rttm"
    file.write_text(
        "SPEAKER dummy 1 1.5 0.5 <NA> <NA> spkB <NA> <NA>\n"
        "SPEAKER dummy 1 0.0 1.5 <NA> <NA> spkA <NA> <NA>\n",
        encoding="utf-8",
    )
    actual = parse_rttm(file)
    assert actual == [
        {"start": 0.0, "end": 1.5, "speaker": "spkA"},
        {"start": 1.5, "end": 2.0, "speaker": "spkB"},
    ]
