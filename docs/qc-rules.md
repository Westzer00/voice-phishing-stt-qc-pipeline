# QC Router

이 저장소의 규칙은 기업연계 프로젝트에서 사용한 오류 의심 구간 선별 방식을 공개 가능한 작은 모듈로 정리한 것입니다. 실제 기업 서버에 배포한 원본과 동일한 코드라고 주장하지 않습니다.

| Flag | 의미 |
|---|---|
| `LOW_SEG_LOGPROB` | segment 평균 log-probability가 낮음 |
| `HIGH_COMPRESSION` | compression ratio가 높음 |
| `HIGH_NOSPEECH_WITH_TEXT` | no-speech 확률이 높은데 텍스트가 존재 |
| `LONG_SEGMENT` | 비정상적으로 긴 segment |
| `REPEATED_SEGMENT` | 가까운 위치에서 동일 문장이 반복 |
| `LOW_WORD_CONF` | low-confidence word 비중이 높음 |
| `CRITICAL_TERM_LOWCONF` | 중요 표현을 포함한 **발화 전체**에서 신뢰도가 낮은 단어가 하나 이상 발견됨(중요 단어 자체의 오류 판정 아님) |

Flag가 발생해도 text를 자동 교체하지 않습니다. 인접 구간을 context padding과 함께 합쳐 review span으로 넘깁니다.
