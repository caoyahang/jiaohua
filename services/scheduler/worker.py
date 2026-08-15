"""定时任务Worker入口。

独立进程运行（docker-compose中的scheduler服务），
启动BackgroundScheduler并常驻，捕获退出信号优雅停机。

运行方式：
    python -m services.scheduler.worker
"""

import logging
import os
import signal
import threading

from services.scheduler.jobs import create_scheduler

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """启动调度器并阻塞主线程，直到收到SIGINT/SIGTERM。"""
    scheduler = create_scheduler()
    scheduler.start()
    for job in scheduler.get_jobs():
        logger.info("已注册任务: %s (%s) 下次执行: %s", job.name, job.id, job.next_run_time)

    stop_event = threading.Event()

    def _shutdown(signum, frame):
        logger.info("收到信号 %s，正在停止调度器...", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("定时任务Worker已启动，等待任务触发...")
    stop_event.wait()
    scheduler.shutdown(wait=True)
    logger.info("定时任务Worker已退出")


if __name__ == "__main__":
    main()
