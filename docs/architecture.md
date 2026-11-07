# Architecture

```text
Voice call
   │
   ▼
Whisper large-v3
   │
   ├────────────── word timestamps ──────────────┐
   │                                             │
   ▼                                             ▼
STT result                                  NeMo diarization
   │                                             │
   ▼                                             │
High-recall QC router                            │
   │                                             │
   ├─ segment log-probability                    │
   ├─ compression / no-speech                    │
   ├─ low-confidence words                       │
   ├─ domain-critical terms                      │
   ├─ repetition / long segment                  │
   │                                             │
   ▼                                             │
Suspicious spans                                 │
   │                                             │
   ▼                                             ▼
Review-plan builder                    word-level temporal alignment
LOCAL / MULTI_LOCAL / FULL                       │
   │                                             ▼
   ▼                                        speaker turns
Human review UI
   │
   ▼
Corrected STT layer
```

## 설계 원칙

QC flag는 자동 수정 명령이 아니라 **검수 우선순위 신호**입니다. 숫자·금액·기관명처럼 오류 비용이 큰 표현은 word confidence와 함께 더 보수적으로 확인합니다.

Diarization 결과는 Whisper segment에 직접 붙이지 않고, word timestamp와 화자 interval의 시간 겹침을 계산해 speaker를 배정합니다. 이후 인접 단어를 turn으로 합칩니다. 잘못된 단어 시작·종료 시각(NaN·음수·역전 포함)은 정렬하기 전에 거절합니다.
