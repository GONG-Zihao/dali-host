from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from app.core.config import get_app_config
from app.core.controller import Controller
from app.core.logging.logger import setup_logging
from app.core.schedule.manager import ScheduleManager
from app.i18n import i18n


def _install_signal_handlers(app: QCoreApplication):
    def _handler(_sig, _frame):  # pragma: no cover - OS signal bridge
        app.quit()

    signal.signal(signal.SIGINT, _handler)
    try:
        signal.signal(signal.SIGTERM, _handler)
    except AttributeError:  # pragma: no cover - Windows 没有 SIGTERM
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LiFud DALI Host headless scheduler")
    parser.add_argument("--lang", choices=("zh", "en"), default="zh")
    parser.add_argument("--load-tasks", default=None, help="任务文件路径，默认使用 数据/schedule/tasks.json")
    parser.add_argument("--run", action="store_true", help="启动事件循环并执行任务")
    parser.add_argument("--no-connect", action="store_true", help="跳过自动连接网关")
    args = parser.parse_args(argv)

    root_dir = Path(__file__).resolve().parents[1]
    log_dir = Path.home() / ".dali_host" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging("LiFud-DALI-Headless", log_dir)

    try:
        i18n.load(args.lang)
    except Exception as exc:  # pragma: no cover - i18n 异常只记录
        logger.warning("加载语言包失败：%s", exc)

    app = QCoreApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setApplicationName("LiFud-DALI-Headless")
    _install_signal_handlers(app)

    cfg = get_app_config(root_dir)
    controller = Controller(cfg)

    if not args.no_connect:
        if controller.connect():
            logger.info("网关已连接 (%s)", cfg.get("gateway", {}).get("type", "mock"))
        else:
            logger.warning("网关连接失败，将以未连接状态运行")

    if args.load_tasks:
        store_path = Path(args.load_tasks)
        store_dir = store_path.parent
    else:
        store_dir = root_dir / "数据" / "schedule"
        store_path = store_dir / "tasks.json"

    manager = ScheduleManager(controller, store_dir)
    manager.store_path = store_path
    manager.load()

    manager.message.connect(lambda msg: logger.info("[schedule] %s", msg))

    if not args.run:
        tasks = manager.list()
        if not tasks:
            logger.info("当前没有任务。使用 --run 启动调度循环。")
        else:
            logger.info("当前共 %s 个任务：", len(tasks))
            for task in tasks:
                logger.info("  - %s (enabled=%s, next=%s)", task.name, task.enabled, task.next_run)
        return 0

    logger.info("Headless scheduler running. 按 Ctrl+C 退出。")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

