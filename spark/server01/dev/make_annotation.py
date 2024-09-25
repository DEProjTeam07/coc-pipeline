'''
실제로 Kafka로부터 데이터를 받아서 처리한다.
그런 다음 최신 폴더 path를 받아서 train.json, test.json을 만든다. 

Master, Worker들 모두 AWS S3에 접근하고 
S3에 접근한 데이터를 바탕으로 처리까지 병렬, 분산으로 처리하는 코드 
추가적으로 저수준 API를 사용하지 않고 고수준 API를 사용하는 코드 
MLOps Level로 따지면 1.5단계 
'''

import json
import os 
import math
from zoneinfo import ZoneInfo
from io import BytesIO

import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf
from pyspark.sql.types import StringType
from PIL import Image


# SparkSession 만들기 
spark = SparkSession \
        .builder \
        .appName("kafka_consumer_test") \
        .config("spark.driver.host", "172.31.3.183") \
        .config("spark.driver.bindAddress", "0.0.0.0") \
        .config("spark.driver.port", "7077") \
        .config("spark.executor.instances", "2") \
        .config("spark.jars", "/opt/bitnami/spark/jars/spark-sql-kafka-0-10_2.12-3.5.0.jar,"
                              "/opt/bitnami/spark/jars/kafka-clients-3.5.0.jar,"
                              "/opt/bitnami/spark/jars/commons-pool2-2.11.0.jar,"
                              "/opt/bitnami/spark/jars/metrics-core-3.2.6.jar,"
                              "/opt/bitnami/spark/jars/spark-token-provider-kafka-0-10_2.12-3.5.1.jar") \
        .master("spark://172.31.3.183:7077") \
        .getOrCreate()
        
# Kafka 설정값 
topic_name = "dbserver1.public.folder_log"
bootstrap_servers = "172.31.3.183:9092,172.31.2.37:9092,172.31.0.17:9092"

# spark가 kafka에 있는 데이터 consuming 
kafka_df = spark \
            .read \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("subscribe", topic_name) \
            .option("startingOffsets", "earliest") \
            .load()

# 
# +----+--------------------+-----+---------+------+--------------------+-------------+
# | key|               value|topic|partition|offset|           timestamp|timestampType|
# +----+--------------------+-----+---------+------+--------------------+-------------+
# |NULL|[6B 69 6D 79 6F 7...| test|        0|     0|2024-09-19 08:33:...|            0|
# +----+--------------------+-----+---------+------+--------------------+-------------+
kafka_df.show()



# value 컬럼을 문자열로 변환
decoded_df = kafka_df\
                .selectExpr("CAST(value AS STRING)")\
                    .select("value")\
                        .collect()[-1][0]

# json 형식으로 변환한다. 
decoded_df = json.loads(decoded_df)


print(f"decoded_df : {decoded_df}")
print()
print()
print(f"decoded_df_type : {type(decoded_df)}")


received_path = decoded_df["after"]["path"]

print(f"최신 폴더 path : {received_path}")

# S3 설정
bucket_name = os.getenv('BUCKET_DEV_NAME')

print(f"bucket_name : {bucket_name}")

# S3 클라이언트를 각 워커에서 설정할 수 있도록 boto3.Session()을 사용
def create_s3_client():
    session = boto3.Session()  # boto3.Session()을 사용하여 새로운 세션 생성
    return session.client("s3")

# 이미지 크기 단위 변환
def calculate_image_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# 마지막 수정 시간 변환 (KST)
def format_last_modified_to_kst(last_modified):
    kst_timezone = ZoneInfo("Asia/Seoul")
    last_modified_kst = last_modified.astimezone(kst_timezone)
    return last_modified_kst.strftime('%Y-%m-%d-%H:%M')

# 이미지 가로/세로 크기 추출
def get_image_dimensions(image_body):
    image_data = image_body.read()
    image = Image.open(BytesIO(image_data))
    width, height = image.size
    return width, height

# S3 파일의 메타데이터 추출 함수
def fetch_metadata(file_key):
    s3_client = create_s3_client()
    
    # S3에서 메타데이터 및 이미지 데이터 가져오기
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    size_in_proper_unit = calculate_image_size(response['ContentLength'])
    last_modified_formatted = format_last_modified_to_kst(response['LastModified'])

    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    image_data = BytesIO(response['Body'].read())  # 이미지 데이터를 메모리에 로드
    width, height = get_image_dimensions(image_data)
    
    return size_in_proper_unit, last_modified_formatted, width, height

# UDF로 변환하여 DataFrame 내에서 사용
@udf(StringType())
def udf_fetch_metadata_size(file_key):
    return fetch_metadata(file_key)[0]

@udf(StringType())
def udf_fetch_metadata_last_modified(file_key):
    return fetch_metadata(file_key)[1]

@udf(StringType())
def udf_fetch_metadata_dimensions(file_key):
    width, height = fetch_metadata(file_key)[2], fetch_metadata(file_key)[3]
    return f"{width} * {height}"

# S3에서 파일 목록을 가져오는 함수
def get_list_jpg_files(bucket_name, path):
    s3_client = create_s3_client()
    jpg_files = []
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=path)
    
    for page in pages:
        if 'Contents' in page:
            for content in page['Contents']:
                if content['Key'].endswith('.jpg'):
                    jpg_files.append(content['Key'])
    return jpg_files

# S3 경로에서 이미지 파일 가져오기                                                          
train_good_images = get_list_jpg_files(bucket_name, f'{received_path}train/good/')
train_defective_images = get_list_jpg_files(bucket_name, f'{received_path}train/defective/')
test_good_images = get_list_jpg_files(bucket_name, f'{received_path}test/good/')
test_defective_images = get_list_jpg_files(bucket_name, f'{received_path}test/defective/')

# DataFrame으로 변환
image_files_df = spark.createDataFrame(
    [(file_key, 1, bucket_name) for file_key in train_good_images] +
    [(file_key, 0, bucket_name) for file_key in train_defective_images] +
    [(file_key, 1, bucket_name) for file_key in test_good_images] +
    [(file_key, 0, bucket_name) for file_key in test_defective_images]
).toDF("FilePath", "label_value", "Bucket")

# UDF를 사용해 메타데이터 컬럼 추가
metadata_df = image_files_df \
    .withColumn("Size", udf_fetch_metadata_size(col("FilePath"))) \
    .withColumn("LastModified", udf_fetch_metadata_last_modified(col("FilePath"))) \
    .withColumn("Dimensions", udf_fetch_metadata_dimensions(col("FilePath")))

# train과 test 데이터 분리 (FilePath 기준으로 'train'과 'test'를 필터링)
train_df = metadata_df.filter(col('FilePath').contains('/train/'))
test_df = metadata_df.filter(col('FilePath').contains('/test/'))

# 최종 JSON 구조로 변환하는 함수
def create_annotation_json(ver_info, type, metadata_df):
    # collect로 모든 데이터를 리스트로 가져옴
    data = metadata_df.collect()
    
    # 각 데이터는 Row 객체이므로 딕셔너리로 변환
    data_dicts = [row.asDict() for row in data]
    
    # 최종 JSON 구조 생성
    annotation = {
        "ver_Info": ver_info,     # 버전 정보
        "type": type,             # 데이터 타입(train or test)
        "annotation": {
            "data": data_dicts    # 메타 데이터 리스트
        }
    }
    return json.dumps(annotation, ensure_ascii=False, indent=4)

# train.json 및 test.json 생성
train_annotation_json = create_annotation_json(received_path, "train", train_df)
test_annotation_json = create_annotation_json(received_path, "test", test_df)

# S3에 업로드
def upload_json_to_s3(bucket_name, dest_s3_path, json_data):
    s3_client = create_s3_client()
    s3_client.put_object(Bucket=bucket_name, Key=dest_s3_path, Body=BytesIO(json_data.encode('utf-8')), ContentType='application/json')

# S3에 업로드 경로 정의
dest_s3_path1 = f"{received_path}train/train.json"
dest_s3_path2 = f"{received_path}test/test.json"

# S3에 업로드
upload_json_to_s3(bucket_name, dest_s3_path1, train_annotation_json)
upload_json_to_s3(bucket_name, dest_s3_path2, test_annotation_json)

print("train.json 데이터가 업로드 되었습니다.")
print("test.json 데이터가 업로드 되었습니다.")
