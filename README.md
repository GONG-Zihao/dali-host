# 莱福德 DALI 上位机（Python + Qt）

一个用 Python + PySide6 开发的 DALI 上位机。提供从设备控制 → 压力测试 → 数据分析 → 配置迁移/定时执行 的闭环能力，并内置双语界面与中文图表字体支持。

> 支持 DALI 两字节前向帧，DT8（Tc / xy / RGBW）；内置 MockTransport 便于开发和无硬件联调。

---

## 功能总览

- 调光（ARC 0–254）：滑条/数值联动，快捷键到 0/128/254
- 变量读写：任意命令字节查询（is_command=1），HEX/DEC 预览
- DT8 控制：
  - Tc 色温（以 Kelvin 输入，内部换算 Mirek）
  - 色彩 xy、RGBW 主色通道（可扩 A/F），预设色板（系统 + 用户自定义合并）
- 组与场景：组成员添加/移除；场景保存/回放/移除
- 指令发送：YAML 快捷命令、自定义两字节帧、历史重放/导入/导出
- 压力测试：ARC 固定/扫描、Scene、DT8 Tc/xy/RGBW；导出 CSV
- 数据分析：时间序列/直方图/累积分布/箱线图；P50/P95/P99 指标；导出 PNG/CSV/JSON
- 定时任务：一次/间隔/每天/每周；动作支持 ARC/Scene/DT8/Raw；未连接自动跳过
- 配置导入导出：组成员、场景亮度、DT8 预设的 JSON 导入/应用/导出
- 一致 UI：状态栏提示、连接门控（未连接时所有“发送/开始”禁用）
- 设备清单：扫描短址、读取组成员位/场景亮度，导出 JSON
- 无界面调度：headless 模式加载/执行定时任务
- 扩展开关：扩展启动后自动安装“语言”切换菜单、网关扫描入口、日志停靠窗格

---

## 安装与运行

环境要求
- Python 3.10–3.12
- 依赖拆分：核心依赖在 `requirements.base.txt`，可选扩展在 `requirements.extras.txt`

首次安装
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 或单独安装：
#   基础依赖：pip install -r requirements.base.txt
#   可选扩展：pip install -r requirements.extras.txt
```

启动（中文/英文）
```bash
python -m app.main --light --lang=zh   # 中文
python -m app.main --light --lang=en   # English
```

无界面调度（可选）
```bash
python -m app.headless --lang=zh              # 列出当前任务概况
python -m app.headless --lang=zh --run        # 启动调度循环（Ctrl+C 退出）
# 指定任务文件
python -m app.headless --lang=zh --run --load-tasks 数据/schedule/tasks.json
```

提示
- 在 VS Code 中选择解释器为 `.venv/bin/python`，并开启自动激活终端后，新终端会自动进入虚拟环境。
- 若提示未找到 PySide6，请确认当前终端已激活 `.venv`，或显式使用 `.venv/bin/python` 运行。

---

## 目录结构

说明：以下为当前仓库的完整结构树，已排除开发环境目录（.venv、.idea、.vscode）与 Python 缓存目录（__pycache__）。运行时生成的导出目录会在下方备注。

```
README.md                                # 项目说明（本文件）
codex_tasks.yaml                          # Codex CLI 任务配置（开发辅助）
enhancedocs/
  DALI上位机项目优化文件.md               # 优化记录与思路笔记
i18n/
  strings.zh.json                         # 中文词条（键值型字典）
  strings.en.json                         # 英文词条
  direct.map.json                         # 直译映射（中↔英，含模板占位）
tools/
  patcher.py                              # 辅助脚本：向入口追加扩展安装代码
requirements.txt                          # 默认安装入口（引用 base）
requirements.base.txt                     # 核心依赖列表
requirements.extras.txt                   # 可选扩展依赖

app/
  main.py                                 # 程序入口：主题/字体/i18n、主窗体、扩展安装
  headless.py                             # 无界面调度入口（命令行）
  i18n.py                                 # I18N 实现：字典 + 直译表 + 模板翻译 + translate_text_to
  assets/
    fonts/
      NotoSansSC-Regular.ttf              # 内置中文字体（分析图表用）
  extensions/
    boot.py                               # 运行时扩展：语言菜单/网关扫描/日志窗格/全局翻译
  gui/
    main_window.py                        # 主窗体：装配各功能面板、工具/帮助菜单
    widgets/
      base_panel.py                       # 基类：状态栏提示、连接门控注册
    panels/
      panel_analysis.py                   # 数据分析：时间序列/直方图/CDF/箱线图 + 导出
      panel_benchmark.py                  # 压力测试：任务参数、线程执行、CSV 导出
      panel_config_io.py                  # 配置导入/导出：组/场景/DT8 预设
      panel_dimming.py                    # 调光（ARC 0–254）
      panel_dt8_color.py                  # DT8 色彩：xy、RGBW（含预设）
      panel_dt8_tc.py                     # DT8 Tc：Kelvin 输入 → Mirek 写入
      panel_groups.py                     # 组管理：加入/移除
      panel_inventory.py                 # 设备扫描/组场景读回
      panel_rw.py                         # 变量读写：命令查询（is_command=1）
      panel_scenes.py                     # 场景：保存/回放/移除
      panel_scheduler.py                  # 定时任务：一次/间隔/每日/每周
      panel_sender.py                     # 指令发送：快捷命令/自定义帧/历史
  experimental/                            # 实验/示例面板（默认不加载）
    panel_addr_alloc.py                   # 地址分配示例
    panel_gateway_scan.py                 # 扫描网关占位（工具菜单调用）
    panel_timecontrol.py                  # 旧版时间控制示例
  core/
    controller.py                         # 上位机核心：将 GUI 动作翻译为传输层帧
    config.py                             # 加载 YAML 配置并填充 opcode/tc 默认值
    dali/
      frames.py                           # 地址字节构造与两字节前向帧
    transport/
      base.py                             # Transport 抽象 + MockTransport（自测用）
      tcp_gateway.py                      # TCP 网关透传实现
      serial_port.py                      # 串口传输（占位）
      hid_gateway.py                      # HID 传输（占位）
    logging/
      logger.py                           # 日志初始化（控制台 + 滚动文件）
    analysis/
      stats.py                            # CSV 读取、统计、ECDF 生成
    bench/
      worker.py                           # 压测线程：信号/统计/CSV 输出桥接
    schedule/
      manager.py                          # 定时任务引擎：计算下一次触发并执行
    io/
      state_io.py                         # 配置 JSON 结构读写（groups/scenes/presets）
      apply.py                            # 将配置应用到设备（组/场景/预设合并）
    utils/
      hexutil.py                          # 帧文本解析与格式化（AA BB）
    presets.py                            # 用户预设合并（配置 + 数据/presets.json）
    events.py                              # 全局事件（连接状态）

配置/
  应用.yaml                                # 应用层配置（预设等）
  连接.yaml                                # 连接/网关参数
  dali.yaml                               # DALI 相关 opcode 与缺省
  commands.yaml                           # 快捷命令定义

数据/
  bench/
    bench_20250916_111802.csv             # 示例/历史压测结果
    bench_20250919_171646.csv             # …
    bench_20250919_171658.csv
    bench_20250919_171711.csv
    bench_20250919_171723.csv
    bench_20250919_171733.csv
    bench_20250919_171743.csv
    bench_20250919_171754.csv
  sender/
    history.json                          # 指令历史（回放/导入导出）
  presets.json                            # 用户自定义 DT8 预设（可选）
  state_template.json                     # 状态模板示例
```

运行时生成（按需）：
- `数据/analysis/`：分析页导出的 PNG/CSV/JSON
- `~/.dali_host/logs/`：应用日志（滚动 5MB×3）
- `数据/schedule/tasks.json`：定时任务持久化

数据目录（按需生成）
- `数据/bench/`：压力测试导出 CSV
- `数据/analysis/`：分析导出的 PNG/CSV/JSON
- `数据/schedule/tasks.json`：定时任务持久化
- `数据/sender/history.json`：指令历史
- `数据/presets.json`：用户自定义 DT8 预设

---

## “设备清单”面板说明

- 扫描：对短址 0..63 做状态查询（Query Status），发现在线设备。
- 读取组：读取 Query Groups 0–7/8–15 的位图；界面显示为“属于的组号列表”。
- 读取场景：读取 0..15 场景的亮度（0..254；255=未编程）；界面显示为“场景号:亮度值”。
- Mock 模式下的数据仅作占位，不代表真实设备状态；要获取准确数据请连接真实网关。

---

## 语言与字体

- 启动参数 `--lang=zh|en`，或运行后通过菜单「语言」切换。
- 分析页使用内置 `Noto Sans SC` 中文字体；若不可用会自动退回英文标签，避免乱码。
- 负号显示已处理（`axes.unicode_minus=False`）。

---

## 配置与快捷命令

示例 `配置/commands.yaml`
```yaml
commands:
  - name: "OFF (ARC=0)"
    type: "arc"
    value: 0
  - name: "Add To Group"
    type: "base_plus_param"
    base: 96        # 0x60 + group
    param: "group"
    min: 0
    max: 15
```

用户预设合并
- 程序启动时将 `配置` 中的预设与 `数据/presets.json` 按名称合并（用户覆盖同名）。

---

## 开发说明

- 主题与外观：默认浅色主题（Qt Fusion + 自定义调色板）。
- 扩展安装：启动后异步安装语言菜单、工具→扫描网关、视图→日志窗格；日志支持导出。
- 连接门控：未连接时相关按钮自动禁用（统一在 `BasePanel.register_send_widgets`）。
- 日志：写入 `~/.dali_host/logs/`（滚动 5MB×3）。
- 依赖：核心见 `requirements.base.txt`，扩展见 `requirements.extras.txt`。
- UI 复用：所有面板统一使用 `AddressTargetWidget` 选择寻址目标（广播/短址/组址）。

本地调试小贴士
- VS Code 选择解释器为 `.venv/bin/python`，设置 `python.terminal.activateEnvironment=true`。
- 无需手动激活也可运行：使用 `.venv/bin/python -m app.main --light --lang=zh`。

---

## 路线图

- 宏录制/回放（动作序列）
- 本地 API（REST/WebSocket）与外部系统联动（可选）
- 传输扩展（串口/HID）与异常恢复（重连、心跳、超时/重试）
- 分析页：CDF 上标注 P50/P95/P99 参考线；报告模板

---

## 许可

暂定位内部项目，待需要对外发布时再添加 `LICENSE` 。
