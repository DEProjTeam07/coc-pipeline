import os
import boto3
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.postgres_hook import PostgresHook
from datetime import datetime, timedelta
import pytz

# S3 클라이언트 생성
s3 = boto3.client('s3')

# 한국 시간대 설정 (UTC+9)
KST = pytz.timezone('Asia/Seoul')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 9, 11),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG 정의
dag = DAG(
    's3_sensor_to_db_dag_ver2',
    default_args=default_args,
    description='S3에서 데이터를 복사하고 DB에 삽입하는 DAG',
    schedule_interval=timedelta(days=1),
    catchup=False,  # 최신 변경 사항만 체크하면 되는거라 밀린거 몰아서 실행하는 기능은 필요없음
)

# 최신 폴더 찾기 함수 (S3)
def get_latest_versioned_folder(bucket_name):
    response = s3.list_objects_v2(Bucket=bucket_name, Delimiter='/')
    
    top_folders = [prefix['Prefix'] for prefix in response.get('CommonPrefixes', []) if prefix['Prefix'].startswith('testver_')]
    
    if not top_folders:
        return None
    
    top_folders_with_dates = []
    for folder in top_folders:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder, MaxKeys=1)
        if 'Contents' in response:
            top_folders_with_dates.append((folder, response['Contents'][0]['LastModified']))
    
    if not top_folders_with_dates:
        return None
    
    latest_folder = max(top_folders_with_dates, key=lambda x: x[1])
    
    return latest_folder[0]

# PostgreSQL에서 가장 최근 폴더 정보 가져오기
def get_latest_folder_from_db():
    try:
        # PostgresHook 사용
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        
        # 가장 최근 폴더 경로를 가져오는 SQL 쿼리
        cursor.execute("SELECT path FROM folder_log ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        cursor.close()

        if result:
            return result[0]  # 가장 최근 폴더의 path 값 반환
        return None
    except Exception as error:
        print(f"Error fetching latest folder from PostgreSQL: {error}")
        return None

# 새로운 폴더가 있는지 확인하는 Task
def task_check_for_new_folder(**kwargs):
    bucket_name = kwargs['bucket_name']
    
    # S3에서 최신 폴더 확인
    latest_folder_s3 = get_latest_versioned_folder(bucket_name)
    
    # PostgreSQL에서 최신 폴더 확인
    latest_folder_db = get_latest_folder_from_db()
    
    if latest_folder_s3 and latest_folder_s3 != latest_folder_db:
        kwargs['ti'].xcom_push(key='new_folder', value=latest_folder_s3)
        print(f"새로운 폴더가 발견되었습니다: {latest_folder_s3}")
    else:
        print("새로운 폴더가 없습니다.")

# S3 객체 복사 Task
def task_copy_directory(**kwargs):
    source_bucket = kwargs['source_bucket']
    destination_bucket = kwargs['destination_bucket']
    new_folder = kwargs['ti'].xcom_pull(task_ids='check_for_new_folder', key='new_folder')
    
    if new_folder:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=source_bucket, Prefix=new_folder)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    source_key = obj['Key']
                    destination_key = source_key.replace(new_folder, new_folder, 1)
                    copy_source = {'Bucket': source_bucket, 'Key': source_key}
                    
                    s3.copy_object(
                        CopySource=copy_source,
                        Bucket=destination_bucket,
                        Key=destination_key
                    )
                    print(f"Copied {source_key} to {destination_key}")

# PostgreSQL에 데이터 삽입 Task (새로운 폴더 정보 기록)
def task_insert_db(**kwargs):
    new_folder = kwargs['ti'].xcom_pull(task_ids='check_for_new_folder', key='new_folder')
    
    if new_folder:
        # PostgresHook 사용
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        
        try:
            current_time_kst = datetime.now(KST)
            insert_query = """
                INSERT INTO folder_log (path, created_at)
                VALUES (%s, %s);
            """
            pg_hook.run(insert_query, parameters=(new_folder, current_time_kst))
            print(f"Inserted {new_folder} into folder_log")
        except Exception as error:
            print(f"Error inserting into PostgreSQL: {error}")

# Task 정의
t1 = PythonOperator(
    task_id='check_for_new_folder',
    python_callable=task_check_for_new_folder,
    op_kwargs={'bucket_name': 'BUCKET_NAME 수정해서 쓰시오'},
    provide_context=True,
    dag=dag,
)

t2 = PythonOperator(
    task_id='copy_directory',
    python_callable=task_copy_directory,
    op_kwargs={'source_bucket': 'BUCKET_NAME 수정해서 쓰시오', 'destination_bucket': 'BUCKET_NAME 수정해서 쓰시오'},
    provide_context=True,
    dag=dag,
)

t3 = PythonOperator(
    task_id='insert_into_db',
    python_callable=task_insert_db,
    provide_context=True,
    dag=dag,
)

# Task 순서 설정
t1 >> t2 >> t3