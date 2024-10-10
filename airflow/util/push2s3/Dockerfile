# Dockerfile
# Python 3.9 Slim 이미지를 베이스로 사용하는 Dockerfile
FROM python:3.9-slim

# 작업 디렉토리를 /app으로 설정
WORKDIR /app

# 로컬 시스템의 rawdata2s3.py 파일을 컨테이너의 /app 디렉토리로 복사
COPY rawdata2s3.py .

# 필요한 패키지 설치 (boto3 및 scikit-learn 설치)
# slim 이미지에는 기본적인 패키지가 없을 수 있으므로, 추가 패키지 설치가 필요할 수 있음
RUN pip install boto3 scikit-learn

# 기본적으로 실행될 명령어를 설정 (기본적으로 rawdata2s3.py 스크립트를 실행)
# CMD ["python", "rawdata2s3.py"]