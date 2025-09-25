from datetime import datetime, timedelta

import pytest
from PySide6.QtCore import QCoreApplication

from app.core.schedule.manager import ScheduleManager, Task


class DummyController:
    def is_connected(self) -> bool:
        return True


@pytest.fixture(scope="module")
def qt_app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def make_manager(tmp_path):
    return ScheduleManager(DummyController(), tmp_path)


def test_interval_next(qt_app, tmp_path):
    mgr = make_manager(tmp_path)
    task = Task(
        id="interval",
        name="interval",
        enabled=True,
        mode="broadcast",
        addr_val=None,
        unaddr=False,
        action="arc",
        params={"value": 128},
        schedule={"type": "interval", "every_ms": 1000},
    )
    now = datetime.now()
    next_dt = mgr._compute_next(task, after=now)
    assert next_dt >= now + timedelta(milliseconds=1000)


def test_daily_next(qt_app, tmp_path):
    mgr = make_manager(tmp_path)
    next_minute = (datetime.now().minute + 1) % 60
    task = Task(
        id="daily",
        name="daily",
        enabled=True,
        mode="broadcast",
        addr_val=None,
        unaddr=False,
        action="arc",
        params={"value": 0},
        schedule={
            "type": "daily",
            "hour": datetime.now().hour,
            "minute": next_minute,
        },
    )
    next_dt = mgr._compute_next(task, after=datetime.now())
    assert next_dt is not None
    assert next_dt.minute == next_minute


def test_weekly_next(qt_app, tmp_path):
    mgr = make_manager(tmp_path)
    weekday = (datetime.now().weekday() + 1) % 7
    task = Task(
        id="weekly",
        name="weekly",
        enabled=True,
        mode="broadcast",
        addr_val=None,
        unaddr=False,
        action="arc",
        params={"value": 254},
        schedule={
            "type": "weekly",
            "hour": 9,
            "minute": 0,
            "weekdays": [weekday],
        },
    )
    next_dt = mgr._compute_next(task, after=datetime.now())
    assert next_dt is not None
    assert next_dt.weekday() == weekday

