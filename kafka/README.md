# DB_CDC_Kafka
- db의 변경사항을 CDC기능으로 kafka클러스터에 producing
- kafka-connect plugin Debezium으로 CDC기능구현
- 구성환경: 3개의 인스턴에 kafka클러스터(Kraft mode), kafka_connet(debezium) 구성 , 3개 중 1개의 인스턴스에 postgres컨테이너(server03) 구성

### 실행 순서
1. kafka 및 kafka-connect 컨테이너 구동

2. pg컨테이너 구동
    - postgres서버(server03)에서 debezium 커넥터 생성
        ```bash
        curl -X POST -H "Content-Type: application/json" \
        -d '{
        "name": "db-connector",  # 커넥터의 이름
        "config": {  # 커넥터의 설정
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",  # 사용할 커넥터 클래스
            "tasks.max": "1",  # 최대 태스크 수
            "database.hostname": "postgres",  # PostgreSQL 서버의 호스트명(컨테이너이름)
            "database.port": "5432",  # PostgreSQL 서버의 포트
            "database.user": "postgres",  # 데이터베이스 사용자 이름
            "database.password": "postgres_password",  # 데이터베이스 비밀번호
            "database.dbname": "db_name",  # 데이터베이스 이름
            "database.server.name": "dbserver1",  # Kafka 내에서 식별할 서버 이름
            "plugin.name": "pgoutput",  # 사용할 플러그인 (before 이미지 수집을 위해)
            "table.whitelist": "public.table_name",  # CDC를 수행할 테이블
            "slot.name": "debezium_slot",  # 사용될 복제 슬롯의 이름
            "database.history.kafka.bootstrap.servers": "localhost:9092",  # Kafka의 Bootstrap 서버 주소
            "database.history.kafka.topic": "dbhistory.db"  # 데이터베이스 변경 이력을 저장할 Kafka 주제
        }
        }' \
        http://localhost:8083/connectors 
        ```
    - debezium 커넥터 상태체크
        ```
        # 커넥터 생태확인
        # 커넥터가 `RUNNING` 상태인지 확인
        curl -X GET http://localhost:8083/connectors/inventory-connector/status | jq

        # 커넥터 삭제
        curl -X DELETE http://localhost:8083/connectors/inventory-connector

    - Kafka consumer를 실행하여, db에 변동 사항이 생길시 CDC에 의해 kafka-cluseter에 변동사항이 들어오는지 확인
        ```bash
        docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 \
        --topic dbserver1.public.table_name \
        --from-beginning
        ```
        ```bash
        # example
        # db에 새로운 데이터가 추가될 시,
        {
            "before":null,
            "after":
            {
                "id":3,
                "path":"/version3","created_at":1726144496000000
            },
            "source":
            {
                "version":"1.9.7.Final",
                "connector":"postgresql",
                "name":"dbserver1",
                "ts_ms":1727077772859,
                "snapshot":"false",
                "db":"inventory",
                "sequence":"["26837704","26838096"]",
                "schema":"public",
                "table":"folder_log",
                "txId":743,
                "lsn":26838096,
                "xmin":null
            },
            "op":"c",
            "ts_ms":1727077773153,
            "transaction":null
        }
        ```


## 추가설명
- 복제 슬롯(Replication Slot)
    - PostgreSQL에서 데이터베이스의 변경사항을 추적하기 위해 사용되는 메커니즘
    - 복제 슬롯(Replication Slot) 종류
        - **물리적 슬롯 (Physical Slot)**:
            - 물리적 슬롯은 WAL(Write Ahead Log) 기록을 사용하여 데이터베이스의 변경사항을 복제합니다.
            - 주로 고가용성(HA) 설정이나 데이터베이스 클러스터 간의 데이터 복제에 사용됩니다.
            - `wal_levle=“replica”`
        - **논리적 슬롯 (Logical Slot)**:
            - 논리적 슬롯은 데이터베이스의 변경사항을 논리적 형태로 제공하여, 특정 테이블의 변경사항만을 선택적으로 복제할 수 있습니다.
            - Debezium과 같은 CDC(Change Data Capture) 도구에서 주로 사용됩니다.
            - 논리적 슬롯은 복제 시 `before`와 `after` 이미지(변경 전후 데이터)를 제공합니다.
            - `wal_levle="logical"`
    - 슬롯 플러그인(Slot PlugIn)
        
        ### 1. `pgoutput` 플러그인
        
        - **용도**: PostgreSQL의 기본 논리적 복제 시스템에서 사용됩니다.
        - **기능**: 데이터베이스 변경 사항을 실시간으로 전송하지만, **이전 상태(before image)**를 제공하지 않습니다. 즉, 데이터가 수정되었을 때 그 수정 이전의 데이터를 알 수 없습니다.
        - **사용 예**: 주로 데이터 복제 및 HA(고가용성) 시스템에서 사용됩니다.
        
        ### 2. `test_decoding` 플러그인
        
        - **용도**: 논리적 복제를 위한 테스트 및 실험 목적으로 설계된 플러그인입니다.
        - **기능**: 데이터 변경 사항을 전송할 때 **이전 상태(before image)**와 **변경된 상태(after image)**를 모두 제공합니다. 즉, 데이터를 수정할 때 변경 이전의 값과 이후의 값을 모두 캡처할 수 있습니다.
        - **사용 예**: CDC(Change Data Capture) 도구, 예를 들어 Debezium과 함께 사용되어 데이터의 변화를 더 세밀하게 추적할 수 있도록 합니다.
    - 현재 구성으로는 `‘test_decoding’` 옵션 사용 불가( debezium plugin이 지원안함)
    - 커넥터 생성시 `"plugin.name"` , `"slot.name"` 옵션으로 자동 생성 시킬수 있음.
    
    ```sql
    # 슬롯 생성
    # SELECT pg_create_logical_replication_slot('slot_name', 'slot_type');
    docker exec -it postgres psql -U postgres -d inventory -c "SELECT pg_create_logical_replication_slot('debezium_slot', 'test_decoding');"
    
    # 슬롯 확인
    # 여러 슬롯이 있을경우, active컬럼이 t인것이 활성화
    docker exec -it postgres psql -U postgres -d inventory -c "SELECT * FROM pg_replication_slots;"
    
    # 슬롯 삭제
    docker exec -it postgres psql -U postgres -d inventory -c "SELECT pg_drop_replication_slot('debezium_slot');"
    ```
    


