# S3에 DataSet 업로드
파이썬 컨테이너를 띄워서 DataSet을 S3로 업로드
### s3에 대한 권한이 필요함
- aws_access_key_id, aws_secret_access_key 를 발급받아야 CLI환경에서 접근할수 있음
- 다른 방법으로는 인트스턴에 IAM권한을 부여하면됨 (ex. AmazonS3FullAccess)

<details>
<summary> 권한설정부분</summary>
    
    ### AWS 자격 증명 설정
    
    - AWS CLI 설치가이드
        - https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
    
    ### AWS 콘솔에서 액세스 키 생성
    
    - **AWS Management Console**에 로그인
    - 우측 상단의 **계정 이름**을 클릭하고 "내 보안 자격 증명(My Security Credentials)"을 선택
    - **"액세스 키(Access keys)"** 섹션으로 스크롤
        - 여기에서 기존 액세스 키를 조회하거나 새로 생성할 수 있습니다.
    - **새 액세스 키 생성(Create New Access Key)** 버튼을 클릭
        - **AWS Access Key ID**와 **AWS Secret Access Key**가 생성
        - **Secret Access Key**는 이때만 확인할 수 있으므로, 반드시 안전한 곳에 저장
    
    ### IAM 사용자 또는 역할 생성
    
    관리형 사용자 또는 역할을 통해 특정 권한을 가진 액세스 키를 생성할 수 있습니다.
    
    - **IAM 서비스**로 이동
    - **사용자(Users)** 탭에서 새 사용자 생성 또는 기존 사용자를 선택
    - **사용자 세부 정보**에서 **보안 자격 증명(Security credentials)** 탭으로 이동
    - **액세스 키(Access keys)** 섹션에서 **새로운 액세스 키 생성(Create access key)**를 클릭
    - 생성된 **Access Key ID**와 **Secret Access Key**를 안전한 곳에 저장
    
    ### 프로그램이나 터미널에서 설정
    
    - **AWS CLI를 통해 설정** (권장):
        - 터미널에 `aws configure` 명령을 입력하면, AWS Access Key ID와 Secret Access Key를 설정할 수 있습니다.
        
        ```bash
        aws configure
        ```
        
        이 명령은 AWS CLI를 사용해 설정 파일에 인증 정보를 저장합니다.
        
    - 환경 변수로 설정
    프로그램 내에서 하드코딩하지 않고, 환경 변수로 설정할 수도 있습니다.
        
        ```bash
        export AWS_ACCESS_KEY_ID=your-access-key-id
        export AWS_SECRET_ACCESS_KEY=your-secret-access-key
        ```        

### IAM권한을 추가하여 S3연결 테스트

- 버킷 리스트 출력해 보는 방법으로 진행

```python
import boto3

# boto3 S3 클라이언트 생성 (IAM 역할을 통해 인증 자동 처리)
s3 = boto3.client('s3')

# 버킷 목록 가져오기
response = s3.list_buckets()

# 버킷 이름 출력
print("S3 버킷 목록:")
for bucket in response['Buckets']:
    print(f"- {bucket['Name']}")
```
</details>


### 누적합 형식으로 split_ver_1, split_ver_2, split_ver_3, split_ver_4
- split_ver_1 -> 0.15
- split_ver_2 -> 0.15 +0.35
- split_ver_3 -> 0.15 +0.35 + 0.20
- split_ver_4 -> 0.15 +0.35 + 0.20 + 0.30

### Container run
```bash
# argparse 라이브러리를 사용하여 명령줄 인자를 처리하고, 인자에 따라 특정 split만 업로드하도록 작성

# build
docker build -t push2s3 .

# DataSet - split_ver_1 
docker run -v /home/ubuntu/raw_data:/app/raw_data push2s3 python rawdata2s3.py 1

# DataSet - split_ver_2
docker run -v /home/ubuntu/raw_data:/app/raw_data push2s3 python rawdata2s3.py 2

# DataSet - split_ver_3
docker run -v /home/ubuntu/raw_data:/app/raw_data push2s3 python rawdata2s3.py 3

# DataSet - split_ver_4
docker run -v /home/ubuntu/raw_data:/app/raw_data push2s3 python rawdata2s3.py 4
```