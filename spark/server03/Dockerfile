# 베이스 이미지로 bitnami/spark:3.5.1 사용
FROM bitnami/spark:3.5.1

# root 사용자 권한으로 전환
USER root

# 필요한 패키지 설치 (curl, wget, ping, net-tools 등) 및 boto3 설치
RUN apt-get update && \
    apt-get install -y curl wget iputils-ping net-tools vim && \
    pip install boto3 Pillow

# Kafka와 연동하기 위한 JAR 파일들을 wget으로 다운로드
RUN wget -P /opt/bitnami/spark/jars \
    https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar && \
    wget -P /opt/bitnami/spark/jars \
    https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.0/kafka-clients-3.5.0.jar && \
    wget -P /opt/bitnami/spark/jars \
    https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.0/commons-pool2-2.11.0.jar && \
    wget -P /opt/bitnami/spark/jars \
    https://repo1.maven.org/maven2/io/dropwizard/metrics/metrics-core/3.2.6/metrics-core-3.2.6.jar && \
    wget -P /opt/bitnami/spark/jars \
    https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.1/spark-token-provider-kafka-0-10_2.12-3.5.1.jar

# spark-prometheus-native metric 모니터링 관련 설정 파일
COPY metrics.properties /opt/bitnami/spark/conf/metrics.properties

# 작업 디렉토리를 /opt/bitnami/spark으로 설정
WORKDIR /opt/bitnami/spark

