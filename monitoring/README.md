# Monitoring 환경구성
- Prometheus: 플렛폼 메트릭 수집
- Grafana: 메트릭 시각화


## server02
- Spark 모니터링(Spark-exporter, * Spark docker-compose.yaml 참고)
- Kafka 모니터링(Kafka-exporter)
    - 카프카브로커 상태 및 debezium커넥터의 상태체크를 모니터링 할 목적으로 구성했지만, debezium커넥터 설정에 어려움이 있어, 카프카브로커 설정만 함.
- 인스턴스 모니터링(node-exporter)
        <img width="1712" alt="image" src="https://github.com/user-attachments/assets/7d0aae34-4ab2-4841-a4e5-2add2cbe4891">

## server04
- 인스턴스 모니터링(node-exporter)
    - server04는 모델 작업하는 서버로 서버 메모리 모니터링 필요에 따라 구성
![image](https://github.com/user-attachments/assets/e334b8fd-827e-4213-8b6f-57055707d8a9)

