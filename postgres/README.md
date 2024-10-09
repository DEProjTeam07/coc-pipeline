# PostgreSQL
Debezium이 db를 감지하기 위한 설정값변경
```bash
# postgres.conf
listen_addresses = '*'
wal_level = logical
max_wal_senders = 4
max_replication_slots = 4
```
외부 접속 허용을 위해  pg_hba.conf 수정
```bash
# pg_hba.conf

#!/bin/bash
echo "host    all    all    0.0.0.0/0    scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
```

### 추가설명
`wal_level` 설정은 PostgreSQL의 Write-Ahead Logging (WAL) 기능의 동작 방식을 지정( 3가지 옵션 값을 지정할수 있음)
  1. minimal:
  - 설명: 이 모드는 WAL 기록을 최소화하여 성능을 최적화합니다. 기본적으로 데이터베이스 복구를 위한 최소한의 정보를 기록합니다.
  - 사용 사례: 단순한 데이터베이스와 일반적인 트랜잭션 환경에서 사용할 수 있습니다. 복제 및 복구가 필요 없는 상황에서 최적입니다.
  2. replica:
  - 설명: 이 모드는 기본적인 스트리밍 복제를 지원합니다. WAL 로그에 복제와 관련된 정보를 기록하여 물리적 복제(예: 슬레이브 서버로 데이터 전송)를 가능하게 합니다.
  - 사용 사례: 기본적인 데이터베이스 복제 및 고가용성을 제공하는 환경에서 사용합니다. 슬레이브 서버에서 데이터를 복제하는 데 필요한 정보를 기록합니다.
  3. logical:
  - 설명: 이 모드는 논리적 복제와 변경 데이터 캡처(CDC)를 지원합니다. WAL에 더 많은 정보를 기록하여 데이터 변경 사항을 추적할 수 있습니다.
  - 사용 사례: Debezium과 같은 CDC 도구를 사용하여 데이터를 다른 시스템으로 스트리밍하거나 논리적 복제를 구현하는 환경에서 필요합니다.
----
#### max_wal_senders:
- PostgreSQL에서 WAL(Write-Ahead Logging) 데이터를 전송하는 프로세스의 최대 개수를 설정합니다.
- WAL 데이터를 전송하는 데에는 복제 작업이나 Debezium의 CDC 작업이 포함됩니다. CDC 작업을 위해 Debezium은 WAL 데이터를 사용하므로, 여러 프로세스가 동시에 WAL 데이터를 사용할 수 있게 하려면 이 값이 높아야 합니다.

#### max_replication_slots:
- 복제 슬롯의 최대 개수를 설정하는 값입니다. Debezium은 PostgreSQL에서 **복제 슬롯(replication slot)**을 사용하여 변경 로그를 유지하고 관리합니다. 이 값을 늘려야 여러 CDC 작업 또는 여러 커넥터가 안정적으로 실행될 수 있습니다.
- 복제 슬롯이 부족하면 CDC 작업을 제대로 수행할 수 없거나 추가적인 복제 슬롯을 생성할 수 없게 됩니다.

