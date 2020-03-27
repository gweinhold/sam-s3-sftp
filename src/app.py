import os
import io
import sys
import json
import paramiko
import boto3
import base64
from botocore.exceptions import ClientError

region_name = os.getenv('AWS_REGION')
s3_bucket = os.getenv('S3_BUCKET_NAME')
s3_file_name = os.getenv('S3_FILE_NAME')
ssm_secret_name = os.getenv('SSM_SECRET_NAME')
target_hostname = os.getenv('TARGET_HOST_NAME')
target_username = os.getenv('TARGET_USER_NAME')
target_path = os.getenv('TARGET_PATH')

# Paramiko client configuration
UseGSSAPI = True  # enable GSS-API / SSPI authentication
DoGSSAPIKeyExchange = True
Port = 22

def get_private_key():
    client = boto3.client('secretsmanager', region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=ssm_secret_name
        )
    except ClientError as e:
        raise e

    else:
        #print(get_secret_value_response)
        secret = get_secret_value_response['SecretString']
        secret_dict = json.loads(secret)
        private_key = secret_dict['PrivateKey']
        
        #Key should be base64 encoded in SecretsManager
        return base64.b64decode(private_key).decode('utf-8')

def copy_file_stream(private_key, user, ip, stream, remote_path):
    source_file = io.BytesIO(stream)
    private_key_str = io.StringIO()
    private_key_str.write(private_key)
    private_key_str.seek(0)

    key = paramiko.RSAKey.from_private_key(private_key_str)

    private_key_str.close()
    del private_key_str

    trans = paramiko.Transport(ip, 22)
    trans.start_client()
    trans.auth_publickey(user, key)

    del key

    #print('Opening transport')
    conn = trans.open_session()

    #print('Opening SFTP session')
    sftp = paramiko.SFTPClient.from_transport(trans)

    print('Copying stream to remote path {}'.format(remote_path))
    sftp.putfo(source_file, remote_path) 

    #print('Closing SFTP session')
    sftp.close()

    #print('Closing transport')
    trans.close()

def get_s3_file(bucket_name, object_name):
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket_name=bucket_name, key=object_name)
    response = obj.get()
    data = response['Body'].read()

    return data

def lambda_handler(event, context):
    target_private_key = get_private_key()
    stream = get_s3_file(s3_bucket, s3_file_name)
    copy_file_stream(target_private_key, target_username, target_hostname, stream, target_path)

    private_key = '##############################################'
    del private_key

    json.dumps({
        "message": "hello world",
    })
