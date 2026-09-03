# Contribution Scope

5인 팀으로 진행한 보이스피싱 AI 프로젝트 중, 이 저장소는 제가 직접 설명 가능한 **STT 품질관리와 Human Review workflow**를 중심으로 정리했습니다.

주요 작업:

- Whisper large-v3 기반 STT 실행 및 품질 분석
- segment / word-level 신뢰도와 도메인 중요 표현을 함께 보는 QC router
- suspicious span 생성과 검수 범위 축소
- NeMo diarization 결과와 Whisper word timestamp의 temporal alignment
- `LOCAL / MULTI_LOCAL / FULL` 기반 audio review plan 구성
- Streamlit 기반 검수 UI 개발 및 운영 개선

전체 서비스의 RAG, 분류, 시나리오 생성 코드를 개인 단독 작업으로 주장하지 않습니다. 비공개 데이터와 내부 prompt도 이 저장소에 포함하지 않습니다.
