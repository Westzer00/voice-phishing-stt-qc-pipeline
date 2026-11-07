from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from src.review_records import make_review_record, reviews_json


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "examples" / "sample_review_plan.csv"
ASR_PATH = ROOT / "examples" / "sample_asr.json"


@st.cache_data
def load_plan() -> pd.DataFrame:
    return pd.read_csv(PLAN_PATH)


@st.cache_data
def load_asr() -> dict:
    return json.loads(ASR_PATH.read_text(encoding="utf-8"))


def format_time(seconds: float) -> str:
    minutes, sec = divmod(int(round(seconds)), 60)
    return f"{minutes:02d}:{sec:02d}"


st.set_page_config(page_title="STT Review Demo", layout="wide")
st.title("Voice Phishing STT · Human Review Demo")
st.caption("합성 텍스트를 사용한 검수 기록 예제 · 실제 통화 음성 및 원문 미포함")

plan = load_plan()
asr = load_asr()

if "reviews" not in st.session_state:
    st.session_state.reviews = {}

completed = len(st.session_state.reviews)
st.progress(completed / max(1, len(plan)))
st.caption(f"처리 완료 {completed} / {len(plan)}")

with st.sidebar:
    st.subheader("검수 필터")
    scopes = st.multiselect(
        "AUDIO_SCOPE",
        ["LOCAL", "MULTI_LOCAL", "FULL"],
        default=["LOCAL", "MULTI_LOCAL", "FULL"],
    )

visible = plan[plan["audio_scope"].isin(scopes)].copy()
if visible.empty:
    st.info("선택한 조건에 해당하는 검수 항목이 없습니다.")
    st.stop()

labels = [f"{row.review_id} · {row.audio_scope}" for row in visible.itertuples()]
selected_label = st.selectbox("검수 항목", labels)
review_id = selected_label.split(" · ", 1)[0]
row = visible[visible["review_id"] == review_id].iloc[0]

left, right = st.columns([1, 1.25])
with left:
    st.markdown("### 🎯 이것만 확인")
    st.info(row["check_instruction"])
    st.metric("AUDIO_SCOPE", row["audio_scope"])
    st.write("검수 구간", f"{format_time(row['start_sec'])} ~ {format_time(row['end_sec'])}")
    st.caption("실제 음성 재생은 포함하지 않은 샘플입니다. 검수 결과 기록 흐름을 확인할 수 있습니다.")

with right:
    st.markdown("### 📝 현재 STT")
    st.code(row["current_text"], language=None)
    st.markdown("### 관련 utterance")
    segment_ids = {int(value) for value in str(row["segment_ids"]).split(";") if value}
    for segment in asr["segments"]:
        if int(segment["id"]) not in segment_ids:
            continue
        st.markdown(
            f"**u{segment['id']} · {format_time(segment['start'])} ~ {format_time(segment['end'])}**"
        )
        st.write(segment["text"])

st.markdown("---")
st.markdown("### 판정")
saved = st.session_state.reviews.get(review_id, {})
choices = [
    "현재 STT 그대로 확정",
    "수정 후 확정",
    "음성에 없는 문장 삭제",
    "구간 전체 재전사",
    "판독 불가 / 추가 검수",
]
choice = st.radio(
    "처리 결과",
    choices,
    index=choices.index(saved.get("decision", choices[0])),
    key=f"decision_{review_id}",
    horizontal=True,
)

correction = st.text_area(
    "수정 내용",
    value=saved.get("correction_text", row["current_text"]),
    key=f"correction_{review_id}",
    disabled=choice != "수정 후 확정",
)

if st.button("검수 결과 기록", type="primary"):
    try:
        record = make_review_record(
            review_id=review_id,
            decision=choice,
            current_text=str(row["current_text"]),
            correction_text=correction,
            audio_scope=str(row["audio_scope"]),
        )
        st.session_state.reviews[review_id] = record
        st.success(f"{review_id} 현재 세션에 검수 결과 기록 완료")
    except ValueError as exc:
        st.error(str(exc))

if st.session_state.reviews:
    st.download_button(
        label="검수 기록 JSON 내려받기",
        data=reviews_json(st.session_state.reviews),
        file_name="sample_review_results.json",
        mime="application/json",
    )
    st.caption("파일 다운로드 전까지 검수 결과는 브라우저 세션에만 유지됩니다.")
