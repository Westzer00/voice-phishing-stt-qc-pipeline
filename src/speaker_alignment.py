from __future__ import annotations

import json
import re
from pathlib import Path


def best_speaker_for_word(
    word_start: float,
    word_end: float,
    diarization: list[dict],
    fallback_sec: float = 0.5,
) -> tuple[str, float]:
    best_speaker = "UNKNOWN"
    best_overlap = 0.0

    for interval in diarization:
        overlap = max(
            0.0,
            min(word_end, float(interval["end"]))
            - max(word_start, float(interval["start"])),
        )
        if overlap > best_overlap:
            best_speaker = str(interval["speaker"])
            best_overlap = overlap

    if best_speaker != "UNKNOWN":
        return best_speaker, best_overlap

    midpoint = (word_start + word_end) / 2
    nearest_speaker = None
    nearest_distance = float("inf")

    for interval in diarization:
        start = float(interval["start"])
        end = float(interval["end"])
        if start <= midpoint <= end:
            return str(interval["speaker"]), 0.0

        distance = min(abs(midpoint - start), abs(midpoint - end))
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_speaker = str(interval["speaker"])

    if nearest_speaker is not None and nearest_distance <= fallback_sec:
        return nearest_speaker, 0.0
    return "UNKNOWN", 0.0


def align_words(
    asr: dict,
    diarization: list[dict],
    turn_gap_sec: float = 0.9,
) -> tuple[list[dict], list[dict]]:
    aligned_words: list[dict] = []

    for segment in asr.get("segments", []):
        for word in segment.get("words", []):
            if word.get("start") is None or word.get("end") is None:
                continue

            start = float(word["start"])
            end = float(word["end"])
            speaker, overlap = best_speaker_for_word(start, end, diarization)
            aligned_words.append(
                {
                    "start": start,
                    "end": end,
                    "word": str(word.get("word") or ""),
                    "probability": word.get("probability"),
                    "speaker": speaker,
                    "speaker_overlap_sec": round(overlap, 4),
                }
            )

    turns: list[dict] = []
    for word in aligned_words:
        gap = None if not turns else word["start"] - turns[-1]["end"]
        new_turn = (
            not turns
            or turns[-1]["speaker"] != word["speaker"]
            or (gap is not None and gap > turn_gap_sec)
        )

        if new_turn:
            turns.append(
                {
                    "speaker": word["speaker"],
                    "start": word["start"],
                    "end": word["end"],
                    "text": word["word"],
                    "word_count": 1,
                }
            )
        else:
            turns[-1]["end"] = word["end"]
            turns[-1]["text"] += word["word"]
            turns[-1]["word_count"] += 1

    for turn in turns:
        turn["start"] = round(float(turn["start"]), 3)
        turn["end"] = round(float(turn["end"]), 3)
        turn["text"] = re.sub(r"\s+", " ", turn["text"]).strip()

    return aligned_words, turns


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Align ASR word timestamps to diarization")
    parser.add_argument("asr_json", type=Path)
    parser.add_argument("diarization_json", type=Path)
    args = parser.parse_args()

    asr = json.loads(args.asr_json.read_text(encoding="utf-8"))
    diarization = json.loads(args.diarization_json.read_text(encoding="utf-8"))
    _, turns = align_words(asr, diarization)
    print(json.dumps(turns, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
