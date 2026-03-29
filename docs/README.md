# 纳米机器人集群区域选择性耦合控制系统

**Region-Selective Coupling Control System for Nanorobot Swarm**

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📋 系统概述

本系统是一套完整的**纳米机器人集群区域选择性耦合控制系统**，实现了：

- ✅ **区域选择性耦合** - 可独立控制多个区域内机器人的耦合行为
- ✅ **多场驱动支持** - 磁场、电场、声场、光场、化学梯度
- ✅ **数值仿真引擎** - 基于有限差分法的动力学仿真
- ✅ **实时可视化** - Web界面实时监控
- ✅ **性能指标评估** - 耦合效率、聚类一致性、能量消耗

---

## 🏗 系统架构

```
nanotorobot_control/
├── src/
│   └── nanorobot_control_system.py    # 核心控制系统
├── visualization/
│   └── web_interface.py                # Web可视化界面
├── models/
│   └── (预留模型扩展)
├── docs/
│   └── README.md
└── requirements.txt
```

---

## 🔬 核心技术

### 1. 区域选择性耦合控制 (Region-Selective Coupling)

**创新点**：与传统的全局耦合控制不同，本系统实现了按区域选择性耦合。

```python
# 核心原理
耦合强度 = f(距离, 区域场强, 激活状态)

# 选择性判定
if 距离 <= 选择性半径:
    建立耦合关系
else:
    保持独立运动
```

### 2. 场耦合动力学模型

支持的场类型：

| 场类型 | 驱动原理 | 应用场景 |
|--------|----------|----------|
| 磁场 | 磁力 F = ∇(m·B) | 磁性纳米粒子 |
| 电场 | 静电 F = qE | 带电粒子 |
| 声场 | 声辐射力 | 超声引导 |
| 光场 | 辐射压力 | 光学捕获 |
| 化学 | 浓度梯度 | 化学趋向 |

### 3. 动力学方程

```
m·a = F_control + F_coupling + F_drag + F_brownian

其中:
- F_control: 控制输入力
- F_coupling: 机器人间耦合作用力
- F_drag: 粘滞阻力 (Stokes drag)
- F_brownian: 布朗运动随机力
```

---

## 🚀 快速开始

### 安装依赖

```bash
pip install numpy matplotlib
```

### 运行核心仿真

```python
from nanorobot_control_system import *

# 创建演示系统
simulator, controller, field_model = create_demo_system()

# 可视化
viz = Visualizer(simulator)
fig = viz.plot_snapshot()
fig2 = viz.plot_metrics()
```

### 运行Web界面

```bash
cd visualization
python web_interface.py 8080
```

然后打开浏览器访问: `http://localhost:8080`

---

## 📖 使用指南

### 1. 自定义仿真参数

```python
# 自定义仿真配置
simulator = run_custom_simulation(
    num_robots=50,        # 机器人数量
    num_regions=3,        # 控制区域数量
    field_type=FieldType.MAGNETIC,  # 场类型
    sim_time=10.0,        # 仿真时长(秒)
    target_pos=(15e-6, 10e-6)  # 目标位置
)
```

### 2. 添加自定义控制区域

```python
controller = RegionSelectiveController()

# 添加圆形控制区域
region_id = controller.add_region(
    center=(5e-6, 5e-6),   # 中心位置 (米)
    radius=2e-6,           # 区域半径 (米)
    field_type=FieldType.MAGNETIC,
    field_strength=1.0,   # 场强系数
    selectivity_radius=1e-6  # 选择性半径
)
```

### 3. 自定义场参数

```python
# 调整场参数
field_model = FieldCouplingModel(FieldType.MAGNETIC)
field_model.params = {
    'coefficient': 1e-12,
    'gradient': 150.0,
    'decay_rate': 0.15
}
```

---

## 📊 性能指标说明

| 指标 | 说明 | 理想值 |
|------|------|--------|
| **Coupling Efficiency** | 已耦合机器人占比 | > 0.8 |
| **Cluster Coherence** | 速度一致性 | > 0.7 |
| **Energy Consumption** | 总动能消耗 | < 0.5 |

---

## 🎮 Web界面功能

- **实时仿真视图**: 观察机器人运动和耦合
- **性能指标**: 实时显示关键指标
- **区域控制**: 开关各区域激活状态
- **参数调节**: 机器人数量、时间流速

---

## 🔧 扩展开发

### 添加新的场类型

```python
class CustomFieldModel(FieldCouplingModel):
    def __init__(self):
        super().__init__(FieldType.HYBRID)
        self.params = {...}  # 自定义参数
    
    def compute_force(self, robot, field_vector, distance):
        # 自定义力计算
        return custom_force
```

### 添加新的控制算法

```python
class AdvancedController(RegionSelectiveController):
    def compute_control_input(self, robot, all_robots, target):
        # 实现自定义控制策略
        return control_force
```

---

## 📚 参考文献

1. Wang, J., & Gao, W. (2022). *Magnetic nanorobots for targeted drug delivery*
2. Nelson, B. J., et al. (2020). *Microrobots: A review of progress*
3. Abbott, J. J., et al. (2009). *How should microrobots swim?*

---

## ⚠️ 注意事项

1. **尺度**: 纳米尺度（10^-9 m），需要考虑布朗运动
2. **环境**: 人体环境温度约 310K
3. **粘度**: 模拟流体环境（水/血液）
4. **精度**: 时间步长建议 < 1μs

---

## 📄 License

MIT License

---

**🦞 作者**: OpenClaw  
**📅 版本**: 1.0.0  
**🔗 主页**: https://github.com/openclaw/nanorobot-control
