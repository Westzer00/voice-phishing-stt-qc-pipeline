import json
import wave
import pytest
from src.nemo_diarization import parse_rttm, validate_wav, write_manifest


def make_wav(path, *, sample_rate=16000, channels=1):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"\0\0" * sample_rate * channels)
    return path


def test_wav_validation_and_manifest(tmp_path):
    wav = make_wav(tmp_path / "sample.wav")
    assert validate_wav(wav) == pytest.approx(1.0)
    target = tmp_path / "subfolder" / "manifest.jsonl"
    write_manifest([wav], target)
    row = json.loads(target.read_text(encoding="utf-8").strip())
    assert row["duration"] == pytest.approx(1.0)
    assert row["audio_filepath"] == str(wav.resolve())
    assert row["num_speakers"] is None


@pytest.mark.parametrize("rate,channels", [(8000, 1), (16000, 2)])
def test_reject_incompatible_audio(tmp_path, rate, channels):
    wav = make_wav(tmp_path / "sample.wav", sample_rate=rate, channels=channels)
    with pytest.raises(ValueError):
        validate_wav(wav)


def test_parse_rttm_sorts_segments_and_assigns_speakers(tmp_path):
    p = tmp_path / "output.rttm"
    p.write_text(
        "SPEAKER fileA 1 2.000 0.250 <NA> <NA> spkB <NA> <NA>\n"
        "SPEAKER fileA 1 0.500 1.000 <NA> <NA> spkA <NA> <NA>\n",
        encoding="utf-8",
    )
    segments = parse_rttm(p)
    assert [(x["speaker"], x["start"], x["end"]) for x in segments] == [
        ("spkA", 0.5, 1.5),
        ("spkB", 2.0, 2.25),
    ]


def test_parse_rttm_rejects_malformed_record(tmp_path):
    p = tmp_path / "bad.rttm"
    p.write_text("SPEAKER truncated\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed RTTM"):
        parse_rttm(p)
