## Airflow 사용이유

- 순차적 작업 처리 
- 데이터 파이프라인 관리 
- 작업 간 의존성 관리 
- 재사용 및 재사용성 향상 
- 작업 오케스트레이션
- 파이선 기반 코드 작성 가능 및 다양한 라이브러리 활용 가능 (ex. Spark, Kafka, AWS boto3 등) 



# S3 Data Pipeline DAG

## 개요

이 Airflow DAG는 S3 버킷에서 데이터를 복사하고 PostgreSQL 데이터베이스에 삽입하는 데이터 파이프라인을 구현합니다. 또한 Spark 작업을 실행하고 GitHub Actions 워크플로우를 트리거합니다.

## 주요 기능

- S3 버킷에서 최신 데이터 폴더 확인
- 새로운 데이터 폴더를 다른 S3 버킷으로 복사
- PostgreSQL 데이터베이스에 새 폴더 정보 기록
- Docker 컨테이너 내에서 Spark 작업 실행
- GitHub Actions 워크플로우 트리거

## DAG 구조

1. **check_for_new_folder**: S3에서 새로운 데이터 폴더 확인
2. **branch_check_for_new_folder**: 새 폴더 유무에 따른 분기 처리
3. **copy_directory**: 새 폴더를 대상 S3 버킷으로 복사
4. **insert_into_db**: PostgreSQL에 새 폴더 정보 삽입
5. **spark_submit_in_container**: Docker 컨테이너에서 Spark 작업 실행
6. **trigger_github_action**: GitHub Actions 워크플로우 트리거

## 설정

- **기본 인수**:
  - 소유자: airflow
  - 시작 날짜: 2024년 9월 11일 (변경할것)
  - 재시도: 1회
  - 재시도 지연: 5분

- **스케줄**: 매일 실행

## 주요 함수

- `get_latest_versioned_folder`: S3에서 최신 버전 폴더 찾기
- `get_latest_folder_from_db`: PostgreSQL에서 최신 폴더 정보 가져오기
- `task_check_for_new_folder`: 새 폴더 확인 및 처리 분기
- `task_copy_directory`: S3 객체 복사
- `task_insert_db`: PostgreSQL에 데이터 삽입
- `spark_submit_in_container`: Docker 컨테이너에서 Spark 작업 실행
- `trigger_github_action`: GitHub Actions 워크플로우 트리거

## 의존성

- Python 라이브러리: boto3, airflow, docker, pytz, re, requests, json
- Airflow 연결: PostgreSQL (postgres_flat_fix)
- Airflow 변수: github_token

## 주의사항

- S3 버킷 이름, GitHub 레포지토리 정보 등은 실제 환경에 맞게 수정해야 합니다.
- 필요한 권한과 인증 정보가 올바르게 설정되어 있어야 합니다.


