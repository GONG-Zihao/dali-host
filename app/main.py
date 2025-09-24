# app/main.py
from __future__ import annotations
import sys
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPalette, QColor, QFont, QFontDatabase
    from PySide6.QtCore import Qt, QTimer
except ModuleNotFoundError as exc:
    if exc.name == "PySide6":
        raise ModuleNotFoundError(
            "PySide6 is missing. Activate your project environment and install dependencies via \n"
            "  python -m pip install -r requirements.txt"
        ) from exc
    raise
import argparse

# 语言与扩展（容错导入）
try:
    from app.i18n import i18n
except Exception:  # 兜底占位，避免启动失败
    class _I:
        def load(self, *_args, **_kwargs):
            pass

    i18n = _I()

try:
    from app.extensions.boot import install_extensions
except Exception:
    install_extensions = None

from app.gui.main_window import MainWindow
from app.core.logging.logger import setup_logging

APP_NAME = "LiFud-DALI上位机"


def apply_light_theme(app: QApplication) -> None:
    """白底黑字的浅色主题"""
    # 1) 清空可能残留的 qdarkstyle/qdarktheme/QSS 等样式
    app.setStyleSheet("")
    # 2) 使用 Qt 的 Fusion 样式并手动设置浅色调色板
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(255, 255, 255))
    pal.setColor(QPalette.WindowText, Qt.black)
    pal.setColor(QPalette.Base, QColor(255, 255, 255))
    pal.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    pal.setColor(QPalette.Text, Qt.black)
    pal.setColor(QPalette.Button, QColor(240, 240, 240))
    pal.setColor(QPalette.ButtonText, Qt.black)
    pal.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    pal.setColor(QPalette.ToolTipText, Qt.black)
    pal.setColor(QPalette.Highlight, QColor(0, 120, 215))
    pal.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(pal)


def apply_chinese_font(app: QApplication) -> None:
    """在系统已安装中文字体的前提下，挑一个可用的全局中文字体"""
    preferred = [
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
        "Microsoft YaHei",
        "SimHei",
    ]
    families = set(QFontDatabase.families())
    for name in preferred:
        if name in families:
            app.setFont(QFont(name, 10))
            break


def main() -> int:
    # 参数解析（兼容未知参数）
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--light", action="store_true", default=False)
    parser.add_argument("--lang", choices=("zh", "en"), default="zh")
    args, _ = parser.parse_known_args()
    # 日志
    log_dir = Path.home() / ".dali_host" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(APP_NAME, log_dir)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # ——外观：白底黑字 + 中文——
    # 若传入 --light 则强制 Light；否则也沿用浅色主题（与现有一致）
    apply_light_theme(app)
    apply_chinese_font(app)

    # 语言（默认 zh，可通过 --lang=en 切换）
    try:
        i18n.load(args.lang)
    except Exception:
        pass

    # 主窗口
    win = MainWindow()
    try:
        # 初始标题应用 i18n（如果资源存在）
        win.setWindowTitle(getattr(i18n, "t", lambda k, fb=None: fb or k)("app.title", APP_NAME))
    except Exception:
        pass
    win.show()

    # 在窗口显示后异步安装扩展（菜单/日志窗格/扫描入口等）
    if install_extensions is not None:
        def _boot():
            try:
                install_extensions(globals())
            except Exception as _e:
                print("[boot] install failed in main():", _e)
        QTimer.singleShot(0, _boot)

    try:
        return app.exec()
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        raise


if __name__ == "__main__":
    sys.exit(main())
