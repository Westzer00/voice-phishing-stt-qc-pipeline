# 변경 내역

## 2026-11-07 — 구조 개편
- 루트 Python 파일을 `src/`로 정리하고 Streamlit UI, 샘플, 테스트 및 문서를 독립 폴더로 분리
- 새 파일 위치에 맞게 테스트 import·UI 입력 경로·README 실행 명령 변경
- GitHub Actions에 Python 단위 테스트와 합성 예제 실행 추가
- 기존 README의 QC 신호, 검수 방식, 화자 정렬 설명은 유지
- 성능 향상 지표는 새로 생성하거나 주장하지 않음: 이번 작업은 재현성과 접근성 개선

구조 개편 이전 상태: `backup/pre-portfolio-restructure-2026-11-07` 브랜치.
