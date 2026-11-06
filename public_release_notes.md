# Public release notes

이 저장소는 프로젝트의 운영 서버 디렉터리를 그대로 복사한 것이 아닙니다.

공개 전 다음 내용을 정리했습니다.

- 내부 서버 경로와 사설 네트워크 주소 제거
- raw audio / transcript / 개인정보성 원천 데이터 제외
- 과거 backup, shell runner, production artifact 경로 제외
- LLM 내부 prompt와 비공개 서비스 설정 제외
- 운영 script에서 QC / alignment / review workflow만 분리
- 예제 데이터는 실제 통화가 아닌 synthetic sample로 교체

루트 Python 모듈의 핵심 로직은 실제 프로젝트 코드의 동작을 보존하면서 공개·리뷰가 쉬운 크기로 리팩터링했습니다.
