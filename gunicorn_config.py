"""
Gunicorn configuration for monitor-ggal
Ensures background thread starts AFTER worker process fork
"""
import os
import threading


def post_fork(server, worker):
    """
    Called after a worker has been forked.
    This is the correct place to start background threads.
    """
    # Import here to avoid executing during parent process
    from app import monitor

    # Only start if not already running
    if not monitor.running:
        print(f"🚀 [Worker {worker.pid}] Starting background monitoring thread")
        monitor.start(intervalo=10)
        print(f"✅ [Worker {worker.pid}] Background thread started successfully")
    else:
        print(f"⚠️  [Worker {worker.pid}] Background thread already running")


# Gunicorn config
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 1
threads = 2
timeout = 120
worker_class = "gthread"
