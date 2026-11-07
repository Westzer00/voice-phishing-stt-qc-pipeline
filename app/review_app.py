from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


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
st.caption("공개용 synthetic data로 구성한 검수 화면입니다. 실제 음성·원문 데이터는 포함하지 않습니다.")

plan = load_plan()
asr = load_asr()

if "done" not in st.session_state:
    st.session_state.done = set()

completed = len(st.session_state.done)
st.progress(completed / max(1, len(plan)))
st.caption(f"처리 완료 {completed} / {len(plan)}")

with st.sidebar:
    st.subheader("검수 필터")
    scopes = st.multiselect(
        "AUDIO_SCOPE",
        ["LOCAL", "MULTI_LOCAL", "FULL"],
        default=["LOCAL", "MULTI_LOCAL", "FULL"],
    )
    padding = st.slider("오디오 앞뒤 여유(초)", 0.0, 5.0, 2.0, 0.5)

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
    st.caption(f"실제 운영 UI에서는 앞뒤 ±{padding:g}초 clip을 ffmpeg cache에서 불러옵니다.")

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
choice = st.radio(
    "처리 결과",
    [
        "현재 STT 그대로 확정",
        "수정 후 확정",
        "음성에 없는 문장 삭제",
        "구간 전체 재전사",
        "판독 불가 / 추가 검수",
    ],
    horizontal=True,
)

correction = st.text_area(
    "수정 내용",
    value=row["current_text"] if choice == "수정 후 확정" else "",
    disabled=choice != "수정 후 확정",
)

if st.button("확정 저장", type="primary"):
    st.session_state.done.add(review_id)
    st.success(f"{review_id} 저장 완료 (demo session only)")
