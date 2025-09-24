from __future__ import annotations
import json, uuid, math
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, Signal, QTimer, QDateTime

# ---- 数据结构 ----
@dataclass
class Task:
    id: str
    name: str
    enabled: bool
    # 目标寻址
    mode: str                    # 'broadcast'|'short'|'group'
    addr_val: Optional[int]      # None/0..63/0..15
    unaddr: bool                 # 仅未寻址（仅广播有用）
    # 动作
    action: str                  # 'arc'|'scene'|'dt8_tc'|'dt8_xy'|'dt8_rgbw'|'raw'
    params: Dict[str, Any] = field(default_factory=dict)
    # 调度
    schedule: Dict[str, Any] = field(default_factory=dict)  # {type: 'once'|'interval'|'daily'|'weekly', ...}
    # 运行时记录
    last_run: Optional[str] = None   # ISO
    next_run: Optional[str] = None   # ISO
    run_count: int = 0

def now_dt() -> datetime:
    return datetime.now()

def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat(timespec="seconds") if dt else None

def parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s: return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

# ---- Manager ----
class ScheduleManager(QObject):
    task_updated = Signal(str)    # task_id
    tasks_reloaded = Signal()
    message = Signal(str)

    def __init__(self, controller, store_dir: Path, parent=None):
        super().__init__(parent)
        self.ctrl = controller
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.store_dir / "tasks.json"
        self._tasks: Dict[str, Task] = {}
        self._timers: Dict[str, QTimer] = {}
        self.load()

    # ---------- 持久化 ----------
    def load(self):
        if self.store_path.exists():
            try:
                data = json.load(open(self.store_path, "r", encoding="utf-8")) or []
                self._tasks.clear()
                for t in data:
                    task = Task(**t)
                    self._tasks[task.id] = task
                self.tasks_reloaded.emit()
            except Exception as e:
                self.message.emit(f"加载任务失败：{e}")
        self._rearm_all()

    def save(self):
        data = [asdict(t) for t in self._tasks.values()]
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- CRUD ----------
    def create(self, name: str, mode: str, addr_val: Optional[int], unaddr: bool,
               action: str, params: Dict[str, Any], schedule: Dict[str, Any], enabled: bool=True) -> str:
        tid = uuid.uuid4().hex
        task = Task(
            id=tid, name=name, enabled=enabled,
            mode=mode, addr_val=addr_val, unaddr=unaddr,
            action=action, params=params, schedule=schedule
        )
        self._tasks[tid] = task
        self._rearm_task(task)
        self.save()
        self.task_updated.emit(tid)
        return tid

    def update(self, tid: str, **fields):
        t = self._tasks.get(tid)
        if not t: return
        # 更新字段
        for k, v in fields.items():
            if hasattr(t, k): setattr(t, k, v)
        # 重新布防
        self._rearm_task(t)
        self.save()
        self.task_updated.emit(tid)

    def delete(self, tid: str):
        t = self._tasks.pop(tid, None)
        self._drop_timer(tid)
        self.save()
        if t: self.task_updated.emit(tid)

    def list(self) -> list[Task]:
        return list(self._tasks.values())

    # ---------- 执行 ----------
    def run_now(self, tid: str):
        t = self._tasks.get(tid)
        if not t: return
        self._execute_task(t)
        # 对于一次性任务，立即禁用
        if (t.schedule or {}).get("type") == "once":
            t.enabled = False
        self._rearm_task(t)
        self.save()
        self.task_updated.emit(tid)

    # ---------- 计时器 ----------
    def _drop_timer(self, tid: str):
        timer = self._timers.pop(tid, None)
        if timer:
            timer.stop()
            timer.deleteLater()

    def _rearm_all(self):
        for t in self._tasks.values():
            self._rearm_task(t)

    def _rearm_task(self, task: Task):
        # 先移除旧timer
        self._drop_timer(task.id)
        # 计算下一次运行
        next_dt = self._compute_next(task)
        task.next_run = iso(next_dt)
        if not task.enabled or not next_dt:
            return
        # 设置单次触发timer，到时执行完再决定下一次
        timer = QTimer(self)
        ms = max(0, int((next_dt - now_dt()).total_seconds() * 1000))
        timer.setSingleShot(True)
        def _fire():
            self._execute_task(task)
            # 更新记录
            task.last_run = iso(now_dt())
            task.run_count += 1
            # 重新计算下一次
            next2 = self._compute_next(task, after=now_dt())
            task.next_run = iso(next2)
            self.save()
            self.task_updated.emit(task.id)
            if task.enabled and next2:
                self._rearm_task(task)  # 继续排下一次
        timer.timeout.connect(_fire)
        timer.start(ms)
        self._timers[task.id] = timer

    # ---------- 调度规则 ----------
    def _compute_next(self, task: Task, after: Optional[datetime] = None) -> Optional[datetime]:
        if not task.enabled: return None
        rule = task.schedule or {}
        typ = (rule.get("type") or "").lower()
        base = after or now_dt()

        if typ == "once":
            dt = parse_iso(rule.get("datetime"))
            if not dt: return None
            if task.last_run:   # 执行过就不再触发
                return None
            return dt if dt > base else None

        if typ == "interval":
            every_ms = int(rule.get("every_ms", 1000))
            if task.last_run:
                last = parse_iso(task.last_run) or base
                next_dt = last + timedelta(milliseconds=every_ms)
            else:
                next_dt = base + timedelta(milliseconds=every_ms)
            return next_dt

        if typ == "daily":
            hh = int(rule.get("hour", 9)); mm = int(rule.get("minute", 0))
            candidate = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if candidate <= base:
                candidate += timedelta(days=1)
            return candidate

        if typ == "weekly":
            # weekdays: [0..6] (Mon=0) + time
            hh = int(rule.get("hour", 9)); mm = int(rule.get("minute", 0))
            days = [int(d) for d in (rule.get("weekdays") or []) if 0 <= int(d) <= 6]
            if not days: return None
            # 找到 >= base 的最近一个
            base_day = base.weekday()
            for delta in range(0, 14):  # 两周窗口内必定命中
                d = (base_day + delta) % 7
                if d in days:
                    candidate = (base + timedelta(days=delta)).replace(hour=hh, minute=mm, second=0, microsecond=0)
                    if candidate > base:
                        return candidate
            return None

        return None

    # ---------- 具体动作 ----------
    def _execute_task(self, task: Task):
        try:
            if not self.ctrl.is_connected():
                self.message.emit(f"任务跳过（未连接）：{task.name}")
                return
            m = task.mode; a = task.addr_val; u = task.unaddr
            act = (task.action or "").lower()
            p = task.params or {}
            if act == "arc":
                v = int(p.get("value", 128))
                self.ctrl.send_arc(m, v, addr_val=a, unaddr=u)
            elif act == "scene":
                sc = int(p.get("scene", 0))
                self.ctrl.scene_recall(m, sc, addr_val=a, unaddr=u)
            elif act == "dt8_tc":
                k = int(p.get("kelvin", 4000))
                self.ctrl.dt8_set_tc_kelvin(m, k, addr_val=a, unaddr=u)
            elif act == "dt8_xy":
                x = float(p.get("x", 0.313)); y = float(p.get("y", 0.329))
                self.ctrl.dt8_set_xy(m, x, y, addr_val=a, unaddr=u)
            elif act == "dt8_rgbw":
                r = int(p.get("r", 0)); g = int(p.get("g", 0)); b = int(p.get("b", 0)); w = int(p.get("w", 0))
                self.ctrl.dt8_set_rgbw(m, r, g, b, w, addr_val=a, unaddr=u)
            elif act == "raw":
                # frames: [[addr,data], ...]
                frames = p.get("frames") or []
                for pair in frames:
                    if isinstance(pair, (list, tuple)) and len(pair) == 2:
                        self.ctrl.send_raw(int(pair[0]), int(pair[1]))
            else:
                self.message.emit(f"未知动作：{act}")
                return
            self.message.emit(f"任务执行：{task.name}")
        except Exception as e:
            self.message.emit(f"任务执行失败：{task.name} -> {e!r}")
