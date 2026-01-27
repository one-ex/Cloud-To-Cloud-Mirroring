import multiprocessing

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'uvicorn.workers.UvicornWorker'

# Bind address
bind = '0.0.0.0:8000'

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stdout
loglevel = 'info'

# Timeouts
timeout = 120  # 2 minutes
keepalive = 5

# Process naming
proc_name = 'cloud-mirror-bot'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
max_requests = 1000
max_requests_jitter = 50