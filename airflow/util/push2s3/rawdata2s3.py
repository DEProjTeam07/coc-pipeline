import os
import boto3
from sklearn.model_selection import train_test_split
from datetime import datetime
import sys

# S3 클라이언트 생성
s3 = boto3.client('s3')
bucket_name = 'deprojteam07-labeledrawdata'

def split_data(files, ratios, split_ratio=(0.8, 0.2), random_state=42):
    """
    데이터를 주어진 비율에 따라 분할하고, 각 분할된 데이터를 train/test로 나눕니다.
    :param files: 분할할 파일 목록
    :param ratios: 분할 비율 (리스트 형식)
    :param split_ratio: train/test 비율 (기본값 0.8:0.2)
    :param random_state: 데이터 분할 시 사용할 랜덤 시드 (재현성을 위해 추가)
    :return: 각 비율로 분할된 데이터셋 목록 (train, test 튜플)
    """
    train_test_splits = []
    start_idx = 0
    total_files = len(files)
    
    for ratio in ratios:
        num_files = int(total_files * ratio)
        split_files = files[start_idx:start_idx + num_files]
        start_idx += num_files
        
        # Train/Test split with random_state
        train_files, test_files = train_test_split(split_files, test_size=split_ratio[1], random_state=random_state)
        train_test_splits.append((train_files, test_files))
    
    return train_test_splits

def generate_new_filename(old_filename, prefix):
    """
    기존 파일 이름에서 숫자를 추출하여 새로운 파일 이름을 생성합니다.
    :param old_filename: 기존 파일 이름 (예: 'good (1).jpg')
    :param prefix: 새로운 파일 이름의 접두사 (예: 'good_', 'defective_')
    :return: 새로운 파일 이름 (예: 'good_00000001.jpg')
    """
    base_name = os.path.splitext(old_filename)[0]
    number = int(base_name.split('(')[-1].strip(')'))
    new_filename = f"{prefix}{number:08}.jpg"
    return new_filename

def upload_to_s3(files, s3_dir, prefix):
    """
    파일들을 주어진 S3 디렉터리에 업로드하고, 업로드에 걸린 시간을 반환합니다.
    :param files: 업로드할 파일 목록
    :param s3_dir: S3 내의 디렉터리 경로
    :param prefix: 새로운 파일 이름의 접두사
    :return: 업로드 시간 (seconds)
    """
    start_time = datetime.now()
    
    for file in files:
        new_filename = generate_new_filename(os.path.basename(file), prefix)
        s3_path = os.path.join(s3_dir, new_filename)
        
        try:
            s3.upload_file(file, bucket_name, s3_path)
            print(f"Uploaded {file} as {s3_path}")
        except Exception as e:
            print(f"Failed to upload {file}: {e}")
    
    end_time = datetime.now()
    upload_time = end_time - start_time
    return upload_time.total_seconds()

# 명령줄 인수 처리
if len(sys.argv) < 2:
    print("Please provide a split number (1-4).")
    sys.exit(1)

split_num = int(sys.argv[1])  # split_ 번호 (1, 2, 3, 4 중 하나)
if split_num not in [1, 2, 3, 4]:
    print("Invalid split number. Please provide a number between 1 and 4.")
    sys.exit(1)

# 디렉터리 경로 설정
good_dir = '/app/raw_data/good'
defective_dir = '/app/raw_data/defective'

good_files = [os.path.join(good_dir, f) for f in os.listdir(good_dir) if f.endswith('.jpg')]
defective_files = [os.path.join(defective_dir, f) for f in os.listdir(defective_dir) if f.endswith('.jpg')]

ratios = [0.15, 0.35, 0.20, 0.30]

# 데이터 분할 (random_state 추가)
good_splits = split_data(good_files, ratios, random_state=42)
defective_splits = split_data(defective_files, ratios, random_state=42)

# 선택된 split에 해당하는 데이터를 모두 합침
train_good = []
test_good = []
train_defective = []
test_defective = []

for i in range(split_num):
    train_good += good_splits[i][0]
    test_good += good_splits[i][1]
    train_defective += defective_splits[i][0]
    test_defective += defective_splits[i][1]

# 선택된 split에 해당하는 데이터를 업로드
split_dir = f"split_ver_{split_num}"

# 업로드 시작 시 S3 디렉토리 경로를 명확히 출력
print(f"Uploading files to S3 directory: {split_dir}")

# 업로드 시간 측정
train_good_time = upload_to_s3(train_good, f'{split_dir}/train/good', 'good_')
test_good_time = upload_to_s3(test_good, f'{split_dir}/test/good', 'good_')
train_defective_time = upload_to_s3(train_defective, f'{split_dir}/train/defective', 'defective_')
test_defective_time = upload_to_s3(test_defective, f'{split_dir}/test/defective', 'defective_')

# 전체 업로드 시간 출력
total_time = train_good_time + test_good_time + train_defective_time + test_defective_time
print(f"Total upload time for {split_dir}: {total_time:.2f} seconds")
