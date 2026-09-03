# 	🛡 Voice Phishing STT QC Pipeline 	🛡

> **Whisper STT · High-Recall QC · NeMo Diarization · Human-in-the-loop Review**

보이스피싱 전화 음성을 STT로 변환한 뒤, **오류 가능성이 높은 구간만 우선 선별하고 사람이 실제 음성을 확인하도록 만든 품질관리 pipeline**입니다.

이 저장소는 프로젝트 전체 서비스가 아니라, 공개 가능한 범위의 **STT / QC / diarization / review workflow**를 취업용으로 정리한 버전입니다.

---

## 1. 왜 별도 QC가 필요했나

Whisper의 confidence가 높아도 금융·수사 도메인의 핵심 단어가 잘못 인식되는 경우가 있었습니다. 그래서 confidence 하나만으로 자동 확정하지 않고 여러 신호를 함께 사용했습니다.

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

**QC flag는 자동 수정 규칙이 아니라 review candidate를 찾기 위한 high-recall screening입니다.**

---

## 2. 프로젝트 규모

최종 프로젝트 기준:

- 전화 음성 **511건** STT 처리
- QC router에서 **5,152개 suspicious candidate segment** 선별
- call-level anomaly **37건** 별도 재검토
- 최종 결과는 자동 출력 그대로 사용하지 않고 Human Review layer를 거쳐 확정

원본 음성과 실제 transcript는 공개하지 않습니다.

---

## 3. Pipeline

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

## 4. High-Recall QC Router

[`src/qc_router.py`](src/qc_router.py)

다음 신호를 조합해 review candidate를 찾습니다.

| Signal | 목적 |
|---|---|
| Segment log-probability | 전체 발화 신뢰도 저하 탐지 |
| Compression ratio | 반복·환각 가능성 확인 |
| No-speech probability | 무음/비음성 구간의 텍스트 생성 확인 |
| Word confidence | 특정 단어 붕괴 탐지 |
| Critical-term check | 숫자·금융·기관/신원 표현을 보수적으로 확인 |
| Repetition | 가까운 구간의 동일 문장 반복 확인 |
| Segment length | 과도하게 긴 segment 확인 |

인접 candidate는 앞뒤 context를 포함해 하나의 listening span으로 병합합니다.

```bash
python -m src.qc_router examples/sample_asr.json
```

---

## 5. Word-level Speaker Alignment

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

## 6. Audio Review Plan

[`src/review_planner.py`](src/review_planner.py)

사람이 모든 통화를 처음부터 끝까지 듣지 않도록 issue 위치를 기준으로 listening window를 만듭니다.

- `LOCAL`: 짧은 한 구간만 확인
- `MULTI_LOCAL`: 떨어진 여러 구간을 각각 확인
- `FULL`: 전체 통화 구조 확인이 실제로 필요한 경우

가까운 issue는 하나의 window로 합치고, 전체 청취는 보수적으로 지정합니다.

---

## 7. Human Review UI

[`app/review_app.py`](app/review_app.py)

운영 UI의 핵심 흐름을 공개용 synthetic data로 재구성했습니다.

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

실제 운영 버전에는 clip caching, ffmpeg 구간 추출, autosave, 다음 미검수 이동 등 검수 속도를 줄이기 위한 기능도 포함했습니다. 공개 repo에서는 데이터·경로 의존성이 큰 부분을 제외했습니다.

---

## 8. NeMo Diarization

[`src/nemo_diarization.py`](src/nemo_diarization.py)

실제 workflow에서 사용한 구성 중 다음 부분을 공개용으로 정리했습니다.

- 16 kHz mono WAV validation
- NeMo inference manifest 생성
- oracle speaker count 사용 안 함
- max speaker 8
- RAM-safe worker / batch 설정
- RTTM parsing

NeMo 전체 config와 checkpoint는 원본 프로젝트에 포함하지 않습니다. 재현 시 NVIDIA NeMo의 telephonic diarization config를 별도로 준비해야 합니다.

---

## 9. Repository 구조

```text
.
├── README.md
├── CONTRIBUTION.md
├── requirements.txt
├── requirements-nemo.txt
├── src/
│   ├── qc_router.py
│   ├── speaker_alignment.py
│   ├── review_planner.py
│   └── nemo_diarization.py
├── app/
│   └── review_app.py
├── examples/
│   ├── sample_asr.json
│   ├── sample_diarization.json
│   └── sample_review_plan.csv
├── tests/
└── docs/
```

---

## 10. 공개 범위

이 저장소에는 다음 자료를 넣지 않았습니다.

- 실제 보이스피싱 음성 / transcript
- 개인정보 또는 원본 corpus
- 내부 서버 주소와 실행 경로
- 비공개 LLM prompt / 서비스 endpoint
- 프로젝트의 모든 팀원 코드
- 과거 backup / 실험용 shell script

공개 전 정리 내용은 [`docs/public_release_notes.md`](docs/public_release_notes.md)에 적었습니다.
