from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


CRITICAL_TERM_RE = re.compile(
    r"(?:\d|원|만원|천원|백만원|천만원|억|"
    r"은행|저축은행|캐피탈|검찰|지검|경찰|금융감독원|금감원|"
    r"계좌|통장|대출|대환|채무|상환|금리|이자|한도|"
    r"이름|성함|수사관|검사|주민|생년|전화번호|계좌번호)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QCRules:
    low_segment_logprob: float = -0.80
    low_word_probability: float = 0.55
    low_word_ratio: float = 0.25
    high_compression_ratio: float = 2.20
    high_no_speech_with_text: float = 0.60
    long_segment_sec: float = 20.0
    span_padding_sec: float = 2.0
    merge_gap_sec: float = 2.0


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def repeated_segment_indices(segments: list[dict], max_distance: int = 5) -> set[int]:
    """Flag nearby exact repetitions without treating them as automatic errors."""
    last_seen: dict[str, int] = {}
    repeated: set[int] = set()

    for index, segment in enumerate(segments):
        text = normalize_text(segment.get("text", ""))
        if len(text) < 8:
            continue

        previous = last_seen.get(text)
        if previous is not None and index - previous <= max_distance:
            repeated.update((previous, index))
        last_seen[text] = index

    return repeated


def flags_for_segment(segment: dict, repeated: bool, rules: QCRules) -> list[str]:
    flags: list[str] = []
    text = str(segment.get("text") or "").strip()
    start = float(segment.get("start") or 0.0)
    end = float(segment.get("end") or start)

    avg_logprob = segment.get("avg_logprob")
    compression = segment.get("compression_ratio")
    no_speech = segment.get("no_speech_prob")

    if avg_logprob is not None and float(avg_logprob) < rules.low_segment_logprob:
        flags.append("LOW_SEG_LOGPROB")
    if compression is not None and float(compression) > rules.high_compression_ratio:
        flags.append("HIGH_COMPRESSION")
    if text and no_speech is not None and float(no_speech) > rules.high_no_speech_with_text:
        flags.append("HIGH_NOSPEECH_WITH_TEXT")
    if end - start > rules.long_segment_sec:
        flags.append("LONG_SEGMENT")
    if repeated:
        flags.append("REPEATED_SEGMENT")

    words = [
        word
        for word in segment.get("words", [])
        if word.get("probability") is not None and str(word.get("word") or "").strip()
    ]
    if words:
        low_words = [
            word for word in words
            if float(word["probability"]) < rules.low_word_probability
        ]
        if len(low_words) >= 2 and len(low_words) / len(words) >= rules.low_word_ratio:
            flags.append("LOW_WORD_CONF")
        if CRITICAL_TERM_RE.search(text) and low_words:
            flags.append("CRITICAL_TERM_LOWCONF")

    return flags


def merge_spans(
    spans: Iterable[dict],
    duration_sec: float | None,
    rules: QCRules,
) -> list[dict]:
    ordered = sorted(spans, key=lambda item: (item["start_sec"], item["end_sec"]))
    merged: list[dict] = []

    for span in ordered:
        start = max(0.0, float(span["start_sec"]) - rules.span_padding_sec)
        end = float(span["end_sec"]) + rules.span_padding_sec
        if duration_sec is not None:
            end = min(duration_sec, end)

        current = {
            "start_sec": start,
            "end_sec": end,
            "reasons": set(span.get("reasons", [])),
            "segment_ids": set(span.get("segment_ids", [])),
            "texts": [str(span.get("text") or "").strip()],
        }

        if merged and start <= merged[-1]["end_sec"] + rules.merge_gap_sec:
            previous = merged[-1]
            previous["end_sec"] = max(previous["end_sec"], end)
            previous["reasons"].update(current["reasons"])
            previous["segment_ids"].update(current["segment_ids"])
            if current["texts"][0]:
                previous["texts"].append(current["texts"][0])
        else:
            merged.append(current)

    return [
        {
            "start_sec": round(item["start_sec"], 3),
            "end_sec": round(item["end_sec"], 3),
            "reasons": sorted(item["reasons"]),
            "segment_ids": sorted(item["segment_ids"]),
            "text": normalize_text(" ".join(item["texts"])),
        }
        for item in merged
    ]


def route_segments(asr: dict, rules: QCRules | None = None) -> list[dict]:
    rules = rules or QCRules()
    segments = asr.get("segments", [])
    repeated = repeated_segment_indices(segments)
    candidates: list[dict] = []

    for index, segment in enumerate(segments):
        reasons = flags_for_segment(segment, index in repeated, rules)
        if not reasons:
            continue
        candidates.append(
            {
                "start_sec": float(segment.get("start") or 0.0),
                "end_sec": float(segment.get("end") or 0.0),
                "reasons": reasons,
                "segment_ids": [int(segment.get("id", index))],
                "text": str(segment.get("text") or "").strip(),
            }
        )

    duration = asr.get("duration_sec")
    if duration is None:
        duration = (asr.get("asr_info") or {}).get("duration_sec")
    duration = float(duration) if duration not in (None, "") else None
    return merge_spans(candidates, duration, rules)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Route suspicious ASR spans for review")
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    asr = json.loads(args.input_json.read_text(encoding="utf-8"))
    result = route_segments(asr)
    payload = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
