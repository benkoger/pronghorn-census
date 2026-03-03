import multiprocessing
import os 
import sys
import gevent.monkey

bind = '0.0.0.0:8000'
workers = os.environ.get('NUM_API_WORKERS') or multiprocessing.cpu_count() *2 + 1
worker_class = 'gevent'
worker_connections = 2000

def when_ready(server):
    gevent.monkey.patch_all()

def post_fork(server, worker):
    from app.extensions import base 
    worker.log.info(f'Creating pool for worker: {worker.pid}')
    base.create_pool(min_size=3, max_size=5)
    worker.log.info(f"worker: {worker.pid}'s pool uuid: {base.pool_uuid}")