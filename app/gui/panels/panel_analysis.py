from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QComboBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit
)
from PySide6.QtCore import Qt, QDateTime

from matplotlib import rcParams, font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.gui.widgets.base_panel import BasePanel
from app.core.analysis.stats import load_durations_csv, compute_stats, ecdf, RunStats
from app.i18n import i18n


def _tr(text: str) -> str:
    # 当缺少可用中文字体时，退回英文标签避免乱码
    if getattr(i18n, "lang", "zh") == "zh" and not _HAS_CN_FONT:
        return i18n.translate_text_to(text, "en")
    return i18n.translate_text(text)


# ------- Matplotlib：确保中文可显示 -------
_FONT_ROOT = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_FONT_CANDIDATES = [
    _FONT_ROOT / "NotoSansSC-Regular.ttf",
    _FONT_ROOT / "NotoSansSC-Regular.otf",
]
_cn_fonts: List[str] = []
_FONT_PROP: Optional[FontProperties] = None

for font_path in _FONT_CANDIDATES:
    if not font_path.exists():
        continue
    try:
        font_manager.fontManager.addfont(str(font_path))
    except Exception:
        # 注册失败时继续尝试创建 FontProperties 以便后续显式使用
        pass
    try:
        prop = FontProperties(fname=str(font_path))
        try:
            family_name = prop.get_name()
        except Exception:
            continue
    except Exception:
        continue
    _FONT_PROP = prop
    if not family_name:
        family_name = font_path.stem
    if family_name not in _cn_fonts:
        _cn_fonts.append(family_name)
    break

for fallback_name in [
    "Noto Sans SC",
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "Microsoft YaHei",
    "SimHei",
    "WenQuanYi Micro Hei",
]:
    if fallback_name not in _cn_fonts:
        _cn_fonts.append(fallback_name)

_available_font_names = {f.name for f in font_manager.fontManager.ttflist}
_selected_family: Optional[str] = None
for name in _cn_fonts:
    if name in _available_font_names:
        _selected_family = name
        break

if _FONT_PROP is None and _selected_family:
    try:
        _FONT_PROP = FontProperties(family=_selected_family)
    except Exception:
        _FONT_PROP = None

existing = rcParams.get('font.sans-serif', [])
if not isinstance(existing, list):
    existing = list(existing)
rcParams['font.sans-serif'] = _cn_fonts + [f for f in existing if f not in _cn_fonts]
rcParams['font.family'] = _cn_fonts + ['sans-serif']
rcParams['axes.unicode_minus'] = False  # 避免负号显示成方块

_HAS_CN_FONT = (_FONT_PROP is not None) or (_selected_family is not None)


class MplCanvas(FigureCanvas):
    def __init__(self, parent: Optional[QWidget] = None):
        fig = Figure(figsize=(6, 4), tight_layout=True)
        super().__init__(fig)
        self.ax = fig.add_subplot(111)


class PanelAnalysis(BasePanel):
    """数据分析页：统计 bench CSV 并可视化。"""

    def __init__(self, controller, statusbar, root_dir: Path):
        super().__init__(controller, statusbar)
        self.root_dir = root_dir
        self.bench_dir = self.root_dir / "数据" / "bench"
        self.out_dir = self.root_dir / "数据" / "analysis"
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self._datasets: List[Dict[str, Any]] = []
        self._plot_modes = [
            ("time_series", "时间序列"),
            ("hist", "直方图"),
            ("cdf", "累积分布"),
            ("box", "箱线图"),
        ]

        self._build_ui()
        self._refresh_bench_list()
        self._apply_language_texts()

    # ---------- 构建 UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # 数据源
        self.box_src = QGroupBox()
        sg = QGridLayout(self.box_src)

        self.list_files = QListWidget()
        self.btn_refresh = QPushButton()
        self.btn_add = QPushButton()
        self.btn_browse = QPushButton()
        self.btn_clear = QPushButton()
        self.ed_dir = QLineEdit(str(self.bench_dir))
        self.ed_dir.setReadOnly(True)
        self.lbl_dir = QLabel()

        self.btn_refresh.clicked.connect(self._refresh_bench_list)
        self.btn_add.clicked.connect(self._add_selected_file)
        self.btn_browse.clicked.connect(self._browse_file)
        self.btn_clear.clicked.connect(self._clear_datasets)

        sg.addWidget(self.lbl_dir, 0, 0)
        sg.addWidget(self.ed_dir, 0, 1, 1, 3)
        sg.addWidget(self.btn_refresh, 0, 4)
        sg.addWidget(self.list_files, 1, 0, 1, 5)
        sg.addWidget(self.btn_add, 2, 3)
        sg.addWidget(self.btn_browse, 2, 4)
        root.addWidget(self.box_src)

        # 图表
        self.box_plot = QGroupBox()
        pg = QGridLayout(self.box_plot)
        self.canvas = MplCanvas(self)
        self.cb_kind = QComboBox()
        for mode_id, label in self._plot_modes:
            self.cb_kind.addItem(label, mode_id)
        self.cb_kind.currentIndexChanged.connect(self._redraw)
        self.sp_bins = QSpinBox(); self.sp_bins.setRange(5, 200); self.sp_bins.setValue(30)
        self.sp_bins.valueChanged.connect(self._redraw)
        self.sp_smooth = QSpinBox(); self.sp_smooth.setRange(1, 200); self.sp_smooth.setValue(1)
        self.sp_smooth.valueChanged.connect(self._redraw)
        self.btn_export_fig = QPushButton()
        self.btn_export_fig.clicked.connect(self._export_png)

        self.lbl_kind = QLabel()
        self.lbl_bins = QLabel()
        self.lbl_smooth = QLabel()

        pg.addWidget(self.lbl_kind, 0, 0)
        pg.addWidget(self.cb_kind, 0, 1)
        pg.addWidget(self.lbl_bins, 0, 2)
        pg.addWidget(self.sp_bins, 0, 3)
        pg.addWidget(self.lbl_smooth, 0, 4)
        pg.addWidget(self.sp_smooth, 0, 5)
        pg.addWidget(self.btn_export_fig, 0, 6)
        pg.addWidget(self.canvas, 1, 0, 1, 7)
        root.addWidget(self.box_plot)

        # 表格
        self.box_stat = QGroupBox()
        tg = QGridLayout(self.box_stat)
        self.table = QTableWidget(0, 11)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)

        self.btn_export_csv = QPushButton()
        self.btn_export_json = QPushButton()
        self.btn_export_csv.clicked.connect(self._export_summary_csv)
        self.btn_export_json.clicked.connect(self._export_summary_json)

        tg.addWidget(self.table, 0, 0, 1, 5)
        tg.addWidget(self.btn_export_csv, 1, 3)
        tg.addWidget(self.btn_export_json, 1, 4)
        root.addWidget(self.box_stat)
        root.addStretch(1)

    # ---------- 语言刷新 ----------
    def _apply_language_texts(self):
        self.box_src.setTitle(_tr("数据源（CSV：index,duration_ms）"))
        self.lbl_dir.setText(_tr("默认目录："))
        self.btn_refresh.setText(_tr("刷新列表"))
        self.btn_add.setText(_tr("添加到对比"))
        self.btn_browse.setText(_tr("浏览 CSV…"))
        self.btn_clear.setText(_tr("清空对比"))

        self.box_plot.setTitle(_tr("图表"))
        self.lbl_kind.setText(_tr("图类型："))
        self.lbl_bins.setText(_tr("直方图分箱数："))
        self.lbl_smooth.setText(_tr("平滑窗口（仅时间序列）："))
        self.btn_export_fig.setText(_tr("导出图像 PNG"))

        self.box_stat.setTitle(_tr("统计指标"))
        headers = [
            _tr("名称"), _tr("样本数"), _tr("总时长(ms)"), _tr("均值(ms)"), _tr("标准差(ms)"),
            _tr("最小(ms)"), _tr("P50(ms)"), _tr("P95(ms)"), _tr("P99(ms)"), _tr("最大(ms)"),
            _tr("近似吞吐(次/秒)")
        ]
        for idx, title in enumerate(headers):
            item = self.table.horizontalHeaderItem(idx)
            if item is None:
                item = QTableWidgetItem()
                self.table.setHorizontalHeaderItem(idx, item)
            item.setText(title)
        self.btn_export_csv.setText(_tr("导出摘要 CSV"))
        self.btn_export_json.setText(_tr("导出摘要 JSON"))

        for idx, (_, label) in enumerate(self._plot_modes):
            self.cb_kind.setItemText(idx, _tr(label))

        # 更新组合框 placeholder
        self.btn_clear.setToolTip(_tr("清空对比"))

        self._refresh_table()  # 重新填充表头在翻译后仍保持
        self._redraw()

    # ---------- 文件列表 ----------
    def _refresh_bench_list(self):
        self.list_files.clear()
        if not self.bench_dir.exists():
            self.bench_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(self.bench_dir.glob("bench_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in files:
            ts = QDateTime.fromSecsSinceEpoch(int(p.stat().st_mtime)).toString("yyyy-MM-dd HH:mm:ss")
            QListWidgetItem(f"{p.name}    [{ts}]", self.list_files)

    def _selected_file_path(self) -> Optional[Path]:
        row = self.list_files.currentRow()
        if row < 0:
            return None
        text = self.list_files.item(row).text().split()[0]
        return self.bench_dir / text

    def _add_selected_file(self):
        path = self._selected_file_path()
        if not path:
            self.show_msg(_tr("请先选择一条 CSV"), 1800)
            return
        self._add_dataset(path)

    def _browse_file(self):
        path_str, _ = QFileDialog.getOpenFileName(self, _tr("选择 CSV"), str(self.bench_dir), "CSV (*.csv)")
        if not path_str:
            return
        self._add_dataset(Path(path_str))

    def _add_dataset(self, path: Path):
        try:
            durs = load_durations_csv(path)
            name = path.stem
            stats = compute_stats(name, durs)
            self._datasets.append({
                "name": name,
                "path": str(path),
                "durations": durs,
                "stats": stats,
            })
            self._refresh_table()
            self._redraw()
            self.show_msg(_tr("已添加：{filename}").format(filename=path.name), 1500)
        except Exception as e:
            self.show_msg(_tr("加载失败：{error}").format(error=e), 4000)

    def _clear_datasets(self):
        self._datasets.clear()
        self._refresh_table()
        self._redraw()

    # ---------- 表格 & 导出 ----------
    def _refresh_table(self):
        self.table.setRowCount(len(self._datasets))
        for r, ds in enumerate(self._datasets):
            st: RunStats = ds["stats"]
            vals = [
                st.name,
                st.count,
                f"{st.total_ms:.1f}",
                f"{st.mean_ms:.3f}",
                f"{st.std_ms:.3f}",
                f"{st.min_ms:.3f}",
                f"{st.p50_ms:.3f}",
                f"{st.p95_ms:.3f}",
                f"{st.p99_ms:.3f}",
                f"{st.max_ms:.3f}",
                f"{st.approx_ops_per_s:.2f}",
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))

    def _export_summary_csv(self):
        if not self._datasets:
            self.show_msg(_tr("无数据可导出"), 1800)
            return
        path, _ = QFileDialog.getSaveFileName(self, _tr("导出摘要 CSV"), str(self.out_dir / "summary.csv"), "CSV (*.csv)")
        if not path:
            return
        headers = [
            "名称", "样本数", "总时长(ms)", "均值(ms)", "标准差(ms)", "最小(ms)",
            "P50(ms)", "P95(ms)", "P99(ms)", "最大(ms)", "近似吞吐(次/秒)",
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            for ds in self._datasets:
                st: RunStats = ds["stats"]
                row = [
                    st.name,
                    st.count,
                    st.total_ms,
                    st.mean_ms,
                    st.std_ms,
                    st.min_ms,
                    st.p50_ms,
                    st.p95_ms,
                    st.p99_ms,
                    st.max_ms,
                    st.approx_ops_per_s,
                ]
                f.write(",".join(str(x) for x in row) + "\n")
        self.show_msg(_tr("已导出：{path}").format(path=path), 2000)

    def _export_summary_json(self):
        if not self._datasets:
            self.show_msg(_tr("无数据可导出"), 1800)
            return
        path, _ = QFileDialog.getSaveFileName(self, _tr("导出摘要 JSON"), str(self.out_dir / "summary.json"), "JSON (*.json)")
        if not path:
            return
        data = [ds["stats"].to_dict() for ds in self._datasets]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.show_msg(_tr("已导出：{path}").format(path=path), 2000)

    # ---------- 绘图 ----------
    def _redraw(self):
        ax = self.canvas.ax
        ax.clear()

        if not self._datasets:
            ax.set_title(_tr("无数据"))
            self.canvas.draw()
            return

        kind = self.cb_kind.currentData(Qt.ItemDataRole.UserRole)

        def label(text: str) -> str:
            return _tr(text)

        def apply_axis_fonts():
            if _FONT_PROP is not None:
                for tick in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
                    tick.set_fontproperties(_FONT_PROP)

        if kind == "time_series":
            window = max(1, self.sp_smooth.value())
            for ds in self._datasets:
                durations = ds["durations"]
                ys = self._moving_avg(durations, window) if window > 1 else durations
                xs = list(range(1, len(ys) + 1))
                ax.plot(xs, ys, label=ds["name"])
            ax.set_xlabel(label("序号"), fontproperties=_FONT_PROP)
            ax.set_ylabel(label("时延 (ms)"), fontproperties=_FONT_PROP)
            ax.set_title(label("时间序列"), fontproperties=_FONT_PROP)
            apply_axis_fonts()
        elif kind == "hist":
            for ds in self._datasets:
                ax.hist(ds["durations"], bins=self.sp_bins.value(), alpha=0.5, label=ds["name"])
            ax.set_xlabel(label("时延 (ms)"), fontproperties=_FONT_PROP)
            ax.set_ylabel(label("频数"), fontproperties=_FONT_PROP)
            ax.set_title(label("直方图"), fontproperties=_FONT_PROP)
            apply_axis_fonts()
        elif kind == "cdf":
            for ds in self._datasets:
                xs, ys = ecdf(ds["durations"])
                ax.plot(xs, ys, label=ds["name"])
            ax.set_xlabel(label("时延 (ms)"), fontproperties=_FONT_PROP)
            ax.set_ylabel(label("累计概率"), fontproperties=_FONT_PROP)
            ax.set_title(label("累积分布"), fontproperties=_FONT_PROP)
            apply_axis_fonts()
        elif kind == "box":
            data = [ds["durations"] for ds in self._datasets]
            labels = [ds["name"] for ds in self._datasets]
            ax.boxplot(data, labels=labels, showfliers=True)
            ax.set_ylabel(label("时延 (ms)"), fontproperties=_FONT_PROP)
            ax.set_title(label("箱线图"), fontproperties=_FONT_PROP)
            apply_axis_fonts()
        else:
            ax.set_title(label("无数据"), fontproperties=_FONT_PROP)

        if self._datasets:
            if _FONT_PROP is not None:
                ax.legend(prop=_FONT_PROP)
            else:
                ax.legend()
        self.canvas.draw()

    @staticmethod
    def _moving_avg(vals: List[float], w: int) -> List[float]:
        if w <= 1 or len(vals) <= w:
            return vals
        out: List[float] = []
        acc = sum(vals[:w])
        out.append(acc / w)
        for idx in range(w, len(vals)):
            acc += vals[idx] - vals[idx - w]
            out.append(acc / w)
        return out

    def _export_png(self):
        if not self._datasets:
            self.show_msg(_tr("无图可导出"), 1800)
            return
        kind_label = self.cb_kind.currentText()
        fname = _tr("图_{kind}_{timestamp}.png").format(
            kind=kind_label,
            timestamp=QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss'),
        )
        path, _ = QFileDialog.getSaveFileName(self, _tr("导出图像"), str(self.out_dir / fname), "PNG (*.png)")
        if not path:
            return
        self.canvas.figure.savefig(path, dpi=150)
        self.show_msg(_tr("已导出：{path}").format(path=path), 2000)

    # 供语言切换时调用
    def apply_language(self):
        self._apply_language_texts()
