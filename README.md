# 보이스피싱 음성인식 검수·사람 검토 파이프라인

> **Whisper 음성인식 · 오류 의심 구간 선별 · NeMo 화자 구분 · 사람 검토**

보이스피싱 전화 음성을 STT로 변환한 뒤, **오류 가능성이 높은 구간만 우선 선별하고 사람이 실제 음성을 확인하도록 만든 품질관리 파이프라인**입니다.

EXEM 기업연계 프로젝트에서 **STT 검수 로직, 화자 정렬, 검수 계획과 화면**을 개발했습니다. 개인 개발 코드와 합성 입력 예제로 실행 방법을 정리했습니다.

---

## 1. 해결한 문제

Whisper의 신뢰도가 높게 표시된 문장에서도 기관명·금액·금융용어가 틀리는 사례가 있었습니다. 틀린 문장이 뒤 단계의 검색·분류·생성 결과까지 바꿀 수 있어, 자동 결과를 그대로 확정하는 대신 **의심 구간을 먼저 선별하고 사람이 원음을 확인**하도록 만들었습니다.

```text
ASR output
  │
  ├─ segment log-probability
  ├─ compression ratio
  ├─ no-speech probability
  ├─ word confidence
  ├─ repeated / long segment
  └─ 숫자·금액·기관명 등 critical term
            │
            ▼
      suspicious span
            │
            ▼
       Human Review
```

**QC 표시가 곧 오류 확정은 아닙니다.** 확인이 필요한 구간을 놓치지 않도록 넓게 선별하는 기준입니다.

---

## 2. STT 검수 작업 규모

**개인 담당 처리 범위와 팀 확정 산출물:**

- 전체 **511건**의 통화 중 읽기 가능한 **509건**(약 2,984분)을 대상으로 STT 처리·검수 진행. 2건은 파일을 읽을 수 없어 제외
- 오류 선별·검수 작업을 거쳐 팀에서 최종 **398건**의 검증 데이터셋 확정(개인 담당 로직과 팀 최종 산출물 구분)
- 검수 후보 선별 로직으로 **5,152개 오류 의심 구간** 추출
- 구간만으로 판단하기 어려운 통화 **37건** 전체 재검토 대상으로 분류
- 최종 결과는 자동 출력 그대로 사용하지 않고 Human Review layer를 거쳐 확정

*통화 원본과 실제 전사 내용은 제외.*

---

## 3. 전체 검수 흐름

```text
Voice Call
    │
    ▼
Whisper large-v3
    │
    ├──────── word timestamps ──────────────┐
    │                                       │
    ▼                                       ▼
STT Result                            NeMo Diarization
    │                                       │
    ▼                                       │
High-Recall QC Router                       │
    │                                       │
    ▼                                       ▼
Suspicious Span                 Word-level Speaker Alignment
    │                                       │
    ▼                                       ▼
Audio Review Plan                     Speaker Turns
LOCAL / MULTI_LOCAL / FULL
    │
    ▼
Streamlit Human Review
    │
    ▼
Corrected STT Layer
```

자세한 구조: [`docs/architecture.md`](docs/architecture.md)

---

## 실행 및 테스트

Python 3.11 이상, 저장소 루트에서 실행하는 기준입니다. 실제 음성 파일 대신 `examples/`의 합성 데이터를 사용합니다.

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.qc_router examples/sample_asr.json
python -m src.speaker_alignment examples/sample_asr.json examples/sample_diarization.json
streamlit run app/review_app.py
```

[검수 결과 저장 로직](src/review_records.py) · [검증 테스트](tests/test_review_records.py)

자동 테스트: `.github/workflows/tests.yml` (푸시·PR 시 실행). [GitHub Actions 테스트 결과](https://github.com/Westzer00/voice-phishing-stt-qc-pipeline/actions)에서 실제 실행 기록을 확인할 수 있습니다. NeMo 모델 추론에는 별도 설정이 필요합니다.

## 4. 오류 의심 구간 선별

[`src/qc_router.py`](src/qc_router.py)

다음 신호를 조합해 review candidate를 찾습니다.

| Signal | 목적 |
|---|---|
| Segment log-probability | 전체 발화 신뢰도 저하 탐지 |
| Compression ratio | 반복·환각 가능성 확인 |
| No-speech probability | 무음/비음성 구간의 텍스트 생성 확인 |
| Word confidence | 특정 단어 붕괴 탐지 |
| Critical-term check | 숫자·금융·기관/신원 표현이 포함된 발화에서 다른 단어라도 신뢰도가 낮으면 우선 검수 후보로 지정 |
| Repetition | 가까운 구간의 동일 문장 반복 확인 |
| Segment length | 과도하게 긴 segment 확인 |

이 규칙은 중요 용어 **자체**가 잘못 인식됐다고 판정하는 기능이 아닙니다. 중요 표현이 있는 발화에 낮은 confidence 단어가 공존하면 사람이 먼저 확인하게 하는 보수적인 선별 규칙입니다. 자동 오탈자 수정이나 정확도 향상을 보장하는 지표로 사용하지 않습니다.

인접 candidate는 앞뒤 context를 포함해 하나의 listening span으로 병합합니다.

```bash
python -m src.qc_router examples/sample_asr.json
```

---

## 5. 단어별 화자 정렬

[`src/speaker_alignment.py`](src/speaker_alignment.py)

Whisper segment 단위 speaker assignment 대신 **word timestamp와 diarization interval의 실제 시간 overlap**을 사용합니다.

```text
Whisper word [start, end]
          │
          │ temporal overlap
          ▼
Diarization [start, end, speaker]
          │
          ▼
word → speaker
          │
          ▼
adjacent words → speaker turn
```

시간 경계가 아주 조금 어긋난 경우에는 word midpoint 기준 0.5초 이내의 가장 가까운 diarization interval을 fallback으로 사용합니다.

```bash
python -m src.speaker_alignment \
  examples/sample_asr.json \
  examples/sample_diarization.json
```

---

## 6. 검수 범위 결정

[`src/review_planner.py`](src/review_planner.py)

사람이 모든 통화를 처음부터 끝까지 듣지 않도록 issue 위치를 기준으로 listening window를 만듭니다.

- `LOCAL`: 짧은 한 구간만 확인
- `MULTI_LOCAL`: 떨어진 여러 구간을 각각 확인
- `FULL`: 전체 통화 구조 확인이 실제로 필요한 경우

가까운 issue는 하나의 window로 합치고, 전체 청취는 보수적으로 지정합니다.

---

## 7. 사람 검토 화면

[`app/review_app.py`](app/review_app.py)

합성 전사 텍스트를 사용한 Streamlit 검수 기록 데모입니다. **검수 판정과 수정 문장을 세션에 보관하고 JSON으로 내려받을 수 있습니다.** 실제 음성 재생·서버 저장 기능은 포함하지 않습니다.

```text
검수 지시
  ↓
검수 범위 / AUDIO_SCOPE
  ↓
현재 STT + 관련 utterance
  ↓
판정
  ├─ 현재 STT 확정
  ├─ 수정 후 확정
  ├─ 삭제
  ├─ 구간 재전사
  └─ 추가 검수
```

실행:

```bash
pip install -r requirements.txt
streamlit run app/review_app.py
```

실제 프로젝트에서는 오디오 구간 캐시, ffmpeg 구간 추출, 자동 저장, 다음 미검수 항목 이동 기능을 사용했습니다. 이 예제는 원본 데이터 연결 없이 실행됩니다.

---

## 8. NeMo 화자 구분

[`src/nemo_diarization.py`](src/nemo_diarization.py)

NeMo 화자 분리 실행에서 다룬 설정:

- 16 kHz mono WAV validation
- NeMo inference manifest 생성
- oracle speaker count 사용 안 함
- max speaker 8
- RAM-safe worker / batch 설정
- RTTM parsing

NeMo 전체 config와 checkpoint는 원본 프로젝트에 포함하지 않습니다. 재현 시 NVIDIA NeMo의 telephonic diarization config를 별도로 준비해야 합니다.

---

## 9. 파일 구조

```text
voice-phishing-stt-qc-pipeline/
├── README.md
├── CONTRIBUTION.md
├── .gitignore
├── requirements.txt
├── requirements-nemo.txt
├── src/
│   ├── __init__.py
│   ├── qc_router.py
│   ├── review_planner.py
│   ├── review_records.py
│   ├── speaker_alignment.py
│   └── nemo_diarization.py
├── app/
│   └── review_app.py
├── examples/
│   ├── sample_asr.json
│   ├── sample_diarization.json
│   └── sample_review_plan.csv
├── tests/
│   ├── test_qc_router.py
│   ├── test_review_planner.py
│   ├── test_review_records.py
│   ├── test_nemo_diarization.py
│   ├── test_rttm_edge_cases.py
│   ├── test_streamlit_app.py
│   └── test_speaker_alignment.py
├── docs/
│   ├── architecture.md
│   ├── qc-rules.md
│   ├── public-release-notes.md
│   └── change-log.md
└── .github/workflows/
    └── tests.yml
```

`src/`에는 검수·정렬 코드, `app/`에는 검수 화면, `examples/`에는 합성 입력, `tests/`에는 테스트, `docs/`에는 설계 판단과 변경 내역을 뒀습니다.

---

## 10. 자료 범위

기업 내부 자료와 원본 데이터 제외:

- 실제 보이스피싱 음성 / transcript
- 개인정보 또는 원본 corpus
- 내부 서버 주소와 실행 경로
- 비공개 LLM prompt / 서비스 endpoint
- 프로젝트의 모든 팀원 코드
- 과거 backup / 실험용 shell script

[담당 내역](CONTRIBUTION.md) · [자료 구성](docs/public-release-notes.md)
