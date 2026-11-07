from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewIssue:
    review_id: str
    start_sec: float
    end_sec: float
    segment_ids: tuple[int, ...]
    decision: str
    reason: str = ""


def classify_issue(decision: str, reason: str) -> str:
    reason = (reason or "").lower()
    if decision == "HALLUCINATION_SUSPECT":
        return "HALLUCINATION"
    if decision == "POSSIBLE_DELETION":
        return "POSSIBLE_DELETION"
    if re.search(r"amount|numeric|number|금액|숫자|번호|날짜|시간", reason):
        return "NUMBER_OR_AMOUNT"
    if re.search(r"proper noun|person-name|location|기관명|인명|이름|지명|고유명", reason):
        return "PROPER_NOUN"
    return "ACOUSTIC_AMBIGUITY"


def merge_review_windows(
    issues: list[ReviewIssue],
    duration_sec: float,
    pad_before: float = 2.0,
    pad_after: float = 2.0,
    merge_gap_sec: float = 1.0,
) -> list[dict]:
    windows = []
    for issue in issues:
        start = max(0.0, issue.start_sec - pad_before)
        end = issue.end_sec + pad_after
        if duration_sec > 0:
            end = min(duration_sec, end)
        windows.append([start, end, [issue.review_id]])

    windows.sort(key=lambda item: (item[0], item[1]))
    merged: list[list] = []

    for start, end, ids in windows:
        if not merged or start > merged[-1][1] + merge_gap_sec:
            merged.append([start, end, ids])
            continue
        merged[-1][1] = max(merged[-1][1], end)
        merged[-1][2].extend(ids)

    return [
        {
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "review_ids": ids,
        }
        for start, end, ids in merged
    ]


def choose_audio_scope(
    windows: list[dict],
    duration_sec: float,
    force_full: bool = False,
    full_coverage_ratio: float = 0.70,
    min_full_duration_sec: float = 30.0,
) -> str:
    if force_full:
        return "FULL"
    if not windows:
        return "LOCAL"

    covered = sum(float(w["end_sec"]) - float(w["start_sec"]) for w in windows)
    if duration_sec >= min_full_duration_sec and covered / duration_sec >= full_coverage_ratio:
        return "FULL"
    return "LOCAL" if len(windows) == 1 else "MULTI_LOCAL"


def build_review_plan(
    issues: list[ReviewIssue],
    duration_sec: float,
    force_full: bool = False,
) -> dict:
    windows = merge_review_windows(issues, duration_sec)
    scope = choose_audio_scope(windows, duration_sec, force_full=force_full)

    issue_types = []
    segment_ids: list[int] = []
    for issue in issues:
        issue_type = classify_issue(issue.decision, issue.reason)
        if issue_type not in issue_types:
            issue_types.append(issue_type)
        for segment_id in issue.segment_ids:
            if segment_id not in segment_ids:
                segment_ids.append(segment_id)

    return {
        "audio_scope": scope,
        "windows": windows,
        "issue_types": issue_types,
        "segment_ids": sorted(segment_ids),
    }
