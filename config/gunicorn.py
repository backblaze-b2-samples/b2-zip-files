import multiprocessing
import os
from str2bool import str2bool

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2))
threads = int(os.getenv("PYTHON_MAX_THREADS", 1))
reload = bool(str2bool(os.getenv("WEB_RELOAD", "false")))

loglevel = os.environ.get('GUNICORN_LOGLEVEL', 'info').lower()
