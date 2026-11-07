# QC Router

공개 버전의 규칙은 실제 production code에서 사용한 high-recall screening 로직을 작은 모듈로 분리한 것입니다.

| Flag | 의미 |
|---|---|
| `LOW_SEG_LOGPROB` | segment 평균 log-probability가 낮음 |
| `HIGH_COMPRESSION` | compression ratio가 높음 |
| `HIGH_NOSPEECH_WITH_TEXT` | no-speech 확률이 높은데 텍스트가 존재 |
| `LONG_SEGMENT` | 비정상적으로 긴 segment |
| `REPEATED_SEGMENT` | 가까운 위치에서 동일 문장이 반복 |
| `LOW_WORD_CONF` | low-confidence word 비중이 높음 |
| `CRITICAL_TERM_LOWCONF` | 숫자·금융·기관/신원 표현과 low-confidence word가 함께 존재 |

Flag가 발생해도 text를 자동 교체하지 않습니다. 인접 구간을 context padding과 함께 합쳐 review span으로 넘깁니다.
