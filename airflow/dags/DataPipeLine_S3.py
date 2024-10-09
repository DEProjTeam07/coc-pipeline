import os
import boto3
from airflow import DAG
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.hooks.postgres_hook import PostgresHook
from airflow.models.variable import Variable
from datetime import datetime, timedelta
import docker
import pytz
import re
import requests
import json

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
    'DataPipeLine_S3',
    default_args=default_args,
    description='S3에서 데이터를 복사하고 DB에 삽입하는 DAG',
    schedule_interval=timedelta(days=1),
    catchup=False,
)

# 최신 폴더 찾기 함수 (S3)
def get_latest_versioned_folder(bucket_name):
    response = s3.list_objects_v2(Bucket=bucket_name, Delimiter='/')
    
    top_folders = [prefix['Prefix'] for prefix in response.get('CommonPrefixes', []) if prefix['Prefix'].startswith('split_ver_')]
    
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
        pg_hook = PostgresHook(postgres_conn_id='postgres_flat_fix')
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
    
    # 버전 번호 추출
    version_s3 = extract_version_number_s3(latest_folder_s3) if latest_folder_s3 else None
    version_db = extract_version_number_db(latest_folder_db) if latest_folder_db else None
    
    print(f"S3 최신 폴더: {latest_folder_s3}, 버전: {version_s3}")
    print(f"DB 최신 폴더: {latest_folder_db}, 버전: {version_db}")
    
    if latest_folder_s3 and version_s3 is not None and (version_db is None or version_s3 > version_db):
        kwargs['ti'].xcom_push(key='new_folder', value=latest_folder_s3)
        print(f"새로운 폴더가 발견되었습니다: {latest_folder_s3}")
        return 'process_new_folder'  # 새로운 폴더가 발견된 경우
    else:
        print("새로운 폴더가 없습니다.")
        return 'no_new_folder'  # 새로운 폴더가 없는 경우

def extract_version_number_s3(folder_name):
    # 'split_ver_X' 형식의 폴더 이름에서 숫자를 추출 (끝에 슬래시가 있을 수도 있음)
    match = re.search(r'split_ver_(\d+)/?$', folder_name)
    if match:
        return int(match.group(1))
    return None

def extract_version_number_db(folder_name):
    # 'version_X' 형식의 폴더 이름에서 숫자를 추출 (끝에 슬래시가 있을 수도 있음)
    match = re.search(r'version_(\d+)/?$', folder_name)
    if match:
        return int(match.group(1))
    return None

# S3 객체 복사 Task
def task_copy_directory(**kwargs):
    source_bucket = kwargs['source_bucket']
    destination_bucket = kwargs['destination_bucket']
    new_folder = kwargs['ti'].xcom_pull(task_ids='check_for_new_folder', key='new_folder')
    
    if new_folder:
        converted_folder = convert_folder_name(new_folder)
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=source_bucket, Prefix=new_folder)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    source_key = obj['Key']
                    destination_key = source_key.replace(new_folder, converted_folder, 1)
                    copy_source = {'Bucket': source_bucket, 'Key': source_key}
                    
                    s3.copy_object(
                        CopySource=copy_source,
                        Bucket=destination_bucket,
                        Key=destination_key
                    )
                    print(f"Copied {source_key} to {destination_key}")
        
        # 변환된 폴더 이름을 XCom을 통해 전달
        kwargs['ti'].xcom_push(key='converted_folder', value=converted_folder)

def convert_folder_name(folder_name):
    # 'split_ver_X'를 'version_X'로 변환
    match = re.search(r'split_ver_(\d+)', folder_name)
    if match:
        return f"version_{match.group(1)}/"
    return folder_name

# PostgreSQL에 데이터 삽입 Task (새로운 폴더 정보 기록)
def task_insert_db(**kwargs):
    converted_folder = kwargs['ti'].xcom_pull(task_ids='copy_directory', key='converted_folder')
    
    if converted_folder:
        # PostgresHook 사용
        pg_hook = PostgresHook(postgres_conn_id='postgres_flat_fix')
        
        try:
            current_time_kst = datetime.now(KST)
            insert_query = """
                INSERT INTO folder_log (path, created_at)
                VALUES (%s, %s);
            """
            pg_hook.run(insert_query, parameters=(converted_folder, current_time_kst))
            print(f"Inserted {converted_folder} into folder_log")

            kwargs['ti'].xcom_push(key='converted_folder', value=converted_folder)
        except Exception as error:
            print(f"Error inserting into PostgreSQL: {error}")

# Spark submit 작업을 실행하는 함수 정의
def spark_submit_in_container():
    client = docker.from_env()  # Docker 데몬에 연결
    containers = client.containers.list(filters={"name": "spark-master"})  # 특정 이름을 가진 컨테이너 필터링

    if containers:
        container = containers[0]  # 첫 번째 컨테이너 선택
        result = container.exec_run("/opt/bitnami/spark/bin/spark-submit --master spark://172.31.3.183:7077 --deploy-mode client /opt/bitnami/spark/dev/make_annotation.py")
        print(result.output.decode())  # 실행 결과 출력
    else:
        print("Spark Master 컨테이너를 찾을 수 없습니다.")

# GitHub Action Workflow를 실행하기 위해 Trigger를 실행하는 함수 
def trigger_github_action(**kwargs):
    try:
        # XCom에서 최신 폴더 path 받아오기
        
        folder_path = str(kwargs['ti'].xcom_pull(task_ids='insert_into_db', key='converted_folder'))  # 이전 Task의 return 값 사용
        folder_path = folder_path.rstrip("/") # ex) version_1/를 version_1로 변경 
        print(folder_path)
        if not folder_path:
            raise ValueError("최신 폴더 path를 찾을 수 없습니다.")

        # GitHub API를 위한 설정
        github_token = Variable.get("youngwoo_github_token")  # Airflow Variable에서 GitHub Token 가져오기
        repo_owner = "DEProjTeam07"  # 사용자명 입력
        repo_name = "coc-model"  # 레포지토리명 입력
        kst = pytz.timezone('Asia/Seoul')  # 한국 시간대 (Asia/Seoul)
        current_time_kst = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')  # 현재 한국 시간 가져오기

        # GitHub Actions를 트리거하기 위해 repository_dispatch 이벤트를 사용
        dispatch_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/dispatches"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        dispatch_data = {
            "event_type": "trigger_action",  # GitHub Actions에서 감지할 이벤트 이름
            "client_payload": {  # 추가적으로 보내고 싶은 데이터를 포함
                "message": f"S3에 새로운 데이터 셋이 업데이트 되었습니다. {current_time_kst}",
                "folder_path": folder_path
            }
        }
        dispatch_response = requests.post(dispatch_url, headers=headers, data=json.dumps(dispatch_data))

        if dispatch_response.status_code != 204:
            raise Exception(f"Failed to dispatch event to GitHub Actions: {dispatch_response.text}")

        print("Github Action Workflow가 성공적으로 트리거되었습니다.")

    except Exception as error:
        print(f"Error dispatching event to GitHub Actions: {error}")
        raise

# Task 정의
t1 = PythonOperator(
    task_id='check_for_new_folder',
    python_callable=task_check_for_new_folder,
    op_kwargs={'bucket_name': 'deprojteam07-labeledrawdata'},
    provide_context=True,
    dag=dag,
)

t2 = PythonOperator(
    task_id='copy_directory',
    python_callable=task_copy_directory,
    op_kwargs={'source_bucket': 'deprojteam07-labeledrawdata', 'destination_bucket': 'deprojteam07-datalake'},
    provide_context=True,
    dag=dag,
)

t3 = PythonOperator(
    task_id='insert_into_db',
    python_callable=task_insert_db,
    provide_context=True,
    dag=dag,
)

t4 = PythonOperator(
    task_id='spark_submit_in_container',
    python_callable=spark_submit_in_container,
    dag=dag 
)

t5 = PythonOperator(
    task_id='trigger_github_action',
    python_callable=trigger_github_action,
    provide_context=True,
    dag=dag,
)

# BranchPythonOperator 정의
branch_task = BranchPythonOperator(
    task_id='branch_check_for_new_folder',
    python_callable=task_check_for_new_folder,
    op_kwargs={'bucket_name': 'deprojteam07-labeledrawdata'},
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



# Task 순서 설정
t1 >> branch_task
branch_task >> no_new_folder_task
branch_task >> process_new_folder_task

# 기존의 t2, t3, t4 태스크를 process_new_folder_task에 연결
t2.set_upstream(process_new_folder_task)
t3.set_upstream(t2)
t4.set_upstream(t3)
t5.set_upstream(t4)