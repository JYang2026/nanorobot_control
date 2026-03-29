# 纳米机器人控制系统与仿真平台

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

## 项目简介

这是一个功能完整的**纳米机器人集群区域选择性耦合控制系统**，集成了仿真、可视化和 G 代码生成功能。适用于纳米机器人研究的数值仿真和实际加工控制。

## 核心功能

### 1. 纳米机器人集群控制 (`src/`)
- **区域选择性耦合机制** - 实现纳米机器人在特定区域的精准耦合与解耦
- **分布式协同控制算法** - 多机器人协同决策与路径规划
- **场耦合动力学模型** - 支持磁场、电场、声场、光场、化学梯度等多种驱动方式
- **实时数值仿真引擎** - 高精度物理仿真，支持大规模集群模拟

### 2. 可视化监控 (`visualization/`)
- **Web 界面实时监控** - 浏览器端实时查看机器人状态
- **轨迹可视化** - 动画展示机器人运动路径
- **场分布可视化** - 直观显示驱动场分布
- **交互式控制** - 支持参数调整和场景切换

### 3. 零件加工 G 代码生成 (`blueprint_to_gcode/`)
- **智能图纸识别** - 从 PDF/图像识别零件加工图
- **加工路径自动生成** - 根据几何特征生成最优加工路径
- **G 代码输出** - 兼容 FANUC/Siemens 数控系统的 G 代码
- **仿真可视化** - Three.js 3D 仿真预览

## 技术架构

```
nanorobot_control/
├── src/                          # 纳米机器人控制系统核心
│   └── nanorobot_control_system.py
│
├── visualization/                # 可视化模块
│   └── web_interface.py
│
├── blueprint_to_gcode/           # G代码生成系统
│   ├── core/
│   │   ├── engine.py            # 核心引擎
│   │   ├── doubao_recognizer.py # AI识别
│   │   └── pdf_recognizer.py    # PDF识别
│   ├── api/
│   │   └── app.py               # Web API
│   └── static/
│       └── index.html           # 前端界面
│
├── docs/                         # 文档
│   └── README.md
│
└── models/                        # 模型文件（预留）
```

## 快速开始

### 环境要求

- Python 3.8+
- NumPy
- Flask (用于 Web 服务)
- 浏览器 (用于可视化)

### 安装依赖

```bash
cd nanorobot_control/blueprint_to_gcode
pip install -r requirements.txt
```

### 运行纳米机器人仿真

```bash
cd nanorobot_control/src

# 基本示例
python3 nanorobot_control_system.py
```

### 启动可视化界面

```bash
cd nanorobot_control/visualization

# 启动 Web 服务器
python3 web_interface.py

# 然后在浏览器打开 http://localhost:8080
```

### 启动 G 代码生成系统

```bash
cd nanorobot_control/blueprint_to_gcode

# 方式1: 直接运行
python3 -c "from core.engine import process_blueprint; print(process_blueprint('test.pdf'))"

# 方式2: 启动 Web API
python3 api/app.py
```

## 核心类说明

### Nanorobot (纳米机器人)

```python
from nanorobot_control_system import Nanorobot, Vector2D

robot = Nanorobot(
    id=1,
    position=Vector2D(0, 0),
    velocity=Vector2D(1, 0)
)
```

### Region (区域)

```python
from nanorobot_control_system import Region, RegionType

region = Region(
    id=1,
    center=Vector2D(100, 100),
    radius=50,
    region_type=RegionType.TARGET
)
```

### Field (场)

```python
from nanorobot_control_system import Field, FieldType

field = Field(
    field_type=FieldType.MAGNETIC,
    strength=0.5,
    direction=Vector2D(1, 0)
)
```

## API 参考

### 纳米机器人控制

| 类/方法 | 说明 |
|---------|------|
| `Nanorobot` | 纳米机器人个体模型 |
| `NanorobotSwarm` | 纳米机器人集群 |
| `Region` | 区域定义 |
| `Field` | 驱动场 |
| `SwarmController` | 集群控制器 |

### G 代码生成

| 函数 | 说明 |
|------|------|
| `process_blueprint()` | 处理图纸生成 G 代码 |
| `BlueprintRecognizer` | 图纸识别引擎 |
| `PathGenerator` | 加工路径生成 |
| `GCodeGenerator` | G 代码生成器 |

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

---

作者: OpenClaw  
版本: 1.0.0
