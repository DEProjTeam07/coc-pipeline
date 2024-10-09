## Airflow 사용이유

- 순차적 작업 처리 
- 데이터 파이프라인 관리 
- 작업 간 의존성 관리 
- 재사용 및 재사용성 향상 
- 작업 오케스트레이션
- 파이선 기반 코드 작성 가능 및 다양한 라이브러리 활용 가능 (ex. Spark, Kafka, AWS boto3 등) 




## 출발지 S3의 최신 변경 사항을 감지후(DB 기록 사항과 비교) Task 작성
```python
t1 = PythonOperator(
    task_id='check_for_new_folder',
    python_callable=task_check_for_new_folder,
    op_kwargs={'bucket_name': 'SOURCE_BUCKET_작성필요'},
    provide_context=True,
    dag=dag,
)
```
### 유의 사항: 
- 출발지 S3 에 들어오는 데이터 폴더명과 DB에 기록되는 사항이 다르므로 
정규식으로 처리 하였음 맨 끝 버전과 관련한 사항은 같다는 것을 이용 
 


- 목적지 S3에 COPY Task 작성
```python
t2 = PythonOperator(
    task_id='copy_directory',
    python_callable=task_copy_directory,
    op_kwargs={'source_bucket': 'SOURCE_BUCKET_작성필요', 'destination_bucket': 'DESTINATION_BUCKET_작성필요'},
    provide_context=True,
    dag=dag,
)
```
 목적지의 신규 데이터 경로 DB에 insert Task 작성
```python
t3 = PythonOperator(
    task_id='insert_into_db',
    python_callable=task_insert_db,
    provide_context=True,
    dag=dag,
)
```
 최신 변경 사항 없을 시 분기 처리하여 곧바로 DAG 종료 Task 작성
```python
branch_task = BranchPythonOperator(
    task_id='branch_check_for_new_folder',
    python_callable=task_check_for_new_folder,
    op_kwargs={'bucket_name': 'SOURCE_BUCKET_작성필요'},
    provide_context=True,
    dag=dag,
)

# 새로운 폴더가 없는 경우의 더미 태스크
no_new_folder_task = DummyOperator(
    task_id='no_new_folder',
    dag=dag,
)

# 새로운 폴더가 있는 우의 태스크 (기존의 t2, t3, t4)
process_new_folder_task = DummyOperator(
    task_id='process_new_folder',
    dag=dag,
)
```

 Spark가 데이터를 받아서 train.json, test.json을 수행하는 Application 실행 Task 작성

[CONFIG] Spark 구성  #7 이슈에 구현사항 있으나 다시 언급하였습니다.

```python
t4 = PythonOperator(
    task_id='spark_submit_in_container',
    python_callable=spark_submit_in_container,
    dag=dag 
)
```


전체 흐름 관련 코드입니다

```
# Task 순서 설정
t1 >> branch_task
branch_task >> no_new_folder_task
branch_task >> process_new_folder_task

# 기존의 t2, t3, t4 태스크를 process_new_folder_task에 연결
t2.set_upstream(process_new_folder_task)
t3.set_upstream(t2)
t4.set_upstream(t3)

```

각각 python operator 구동 함수의 경우 코드 리뷰를 통해 확인 부탁드립니다.

