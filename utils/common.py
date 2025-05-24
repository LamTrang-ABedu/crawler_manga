import os
import re
import json
import unicodedata
import boto3
from dotenv import load_dotenv
load_dotenv()

R2_BUCKET = "hopehub-storage"

# === Slugify ===
def slugify(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r'[^a-zA-Z0-9\s-]', '', name).lower()
    return re.sub(r'[\s]+', '-', name).strip()

# === R2 Helpers ===
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY')
    )

def upload_to_r2(key, data):
    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType='application/json'
        )
        # print(f"[UPLOAD] {key} OK")
    except Exception as e:
        print(f"[UPLOAD ERROR] {key}: {e}")

def read_from_r2(key):
    try:
        s3 = get_s3_client()
        res = s3.get_object(Bucket=R2_BUCKET, Key=key)
        return json.loads(res['Body'].read().decode('utf-8'))
    except:
        return []