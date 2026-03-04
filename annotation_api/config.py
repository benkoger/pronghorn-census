import os
from botocore.config import Config
from dotenv import load_dotenv
import redis
from boto3.s3.transfer import TransferConfig

load_dotenv()

class FlaskConfig:
	SECRET_KEY = os.environ.get('SECRET_KEY')
	SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE') or 'Lax'
	SESSION_COOKIE_SECURE = (os.environ.get('SESSION_COOKIE_SECURE') or 'true').lower() in ['true', '1', 't', 'y', 'yes']
	SESSION_TYPE = 'redis'
	SESSION_PERMANENT = (os.environ.get('SESSION_PERMANENT') or 'true').lower() in ['true', '1', 't', 'y', 'yes']
	PERMANENT_SESSION_LIFETIME = 86400 # 24 hours
	SESSION_USE_SIGNER = (os.environ.get('SESSION_USE_SIGNER') or 'true').lower() in ['true', '1', 't', 'y', 'yes']
	SESSION_REDIS = redis.from_url(os.environ.get('SESSION_REDIS'))
	ORIGIN_URL = os.environ.get('ORIGIN_URL') #pyright: ignore 
	BUCKET_NAME = os.environ.get('BUCKET_NAME')
	SESSION_COOKIE_DOMAIN = None 
	SESSION_COOKIE_PATH = '/'
	OAUTH2_PROVIDERS = {
		'google': {
			'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
			'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
			'authorize_url': 'https://accounts.google.com/o/oauth2/auth',
			'token_url': 'https://accounts.google.com/o/oauth2/token',
			'userinfo': {
				'url': 'https://www.googleapis.com/oauth2/v3/userinfo',
				'email': lambda json: json['email'],
			},
			'scopes': ['openid', 'email', 'profile'],
		}
	}

db_config = {
	'dbname': os.environ.get('DB_NAME'),
	'user': os.environ.get('DB_USER'),              
	'password': os.environ.get('DB_PASS'),    
	'host': os.environ.get('DB_HOST'),           
	'port': os.environ.get('DB_PORT'),    
	'options': '-c statement_timeout=5000'        
}

cache_config={
	'CACHE_TYPE': 'RedisCache',
	'CACHE_DEFAULT_TIMEOUT': 300,
	'CACHE_REDIS_HOST': os.environ.get('VALKEY_HOST'),
	'CACHE_REDIS_PORT': 6379,
	'CACHE_REDIS_PASSWORD': os.environ.get('VALKEY_PASS')
}

s3_config = Config(
		signature_version='s3',  # s3v4 is the standard, s3 is an older version
		s3={
				'payload_signing_enabled': True,
				'addressing_style': 'path',
				'request_checksum_calculation': 'when_required',
				'response_checksum_validation': 'when_required' 
			}
	)

transfer_config = TransferConfig(
		use_threads=True,
		multipart_threshold=16 * 1024 * 1024
	)  

