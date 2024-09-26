FROM apache/airflow:2.10.0

# Root 권한으로 작업 수행
USER root

# 필요한 패키지 설치 및 default 사용자를 docker 그룹에 추가
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libsasl2-dev \
        procps && \
    # default 사용자에 Docker 소켓 접근 권한 부여
    # 호스트(로컬)에서 getent group docker를 해서 docker의 그룹 id를 확인하고 여기에서 똑같이 id를 적용 
    groupadd -g 988 docker && \
    usermod -aG docker airflow && \
    apt-get autoremove -yqq --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# 추가 Python 패키지 설치
RUN pip install \
    confluent-kafka==2.5.3 \
    apache-airflow-providers-apache-kafka 
    # 카프카 프로바이더 안쓰긴 하는데 추후에 수정
# 추가 패키지 설치
# argparse 제거
RUN pip uninstall -y argparse
