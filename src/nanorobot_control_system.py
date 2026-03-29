#!/usr/bin/env python3
"""
纳米机器人集群区域选择性耦合控制系统
=====================================
Region-Selective Coupling Control System for Nanorobot Swarm

核心特性:
- 区域选择性耦合机制 (Region-Selective Coupling)
- 分布式协同控制算法
- 场耦合动力学模型 (磁场/电场/声场)
- 实时数值仿真引擎
- 可视化监控界面

作者: OpenClaw
版本: 1.0.0
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Callable
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 第一部分: 核心数据结构与类型定义
# ============================================================

class FieldType(Enum):
    """场类型枚举"""
    MAGNETIC = "magnetic"      # 磁场驱动
    ELECTRIC = "electric"      # 电场驱动
    ACOUSTIC = "acoustic"      # 声场驱动
    OPTICAL = "optical"        # 光驱动
    CHEMICAL = "chemical"      # 化学梯度驱动
    HYBRID = "hybrid"          # 混合场

class CouplingState(Enum):
    """耦合状态"""
    COUPLED = 1      # 已耦合
    DECOUPLING = 2   # 解耦中
    DECOUPLED = 3    # 已解耦
    COUPLING = 4     # 耦合中

@dataclass
class Vector2D:
    """二维向量"""
    x: float = 0.0
    y: float = 0.0
    
    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2D(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float):
        return Vector2D(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar: float):
        return Vector2D(self.x / scalar, self.y / scalar) if scalar != 0 else Vector2D()
    
    def norm(self) -> float:
        try:
            return np.sqrt(self.x**2 + self.y**2)
        except OverflowError:
            return 1e10  # 限制最大值
    
    def normalize(self):
        n = self.norm()
        return self / n if n > 1e-10 else Vector2D()
    
    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y
    
    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y])

@dataclass
class Nanorobot:
    """纳米机器人个体模型"""
    id: int
    position: Vector2D
    velocity: Vector2D = field(default_factory=lambda: Vector2D())
    acceleration: Vector2D = field(default_factory=lambda: Vector2D())
    orientation: float = 0.0          # 朝向角 (弧度)
    angular_velocity: float = 0.0    # 角速度
    
    # 物理参数
    radius: float = 5e-9             # 纳米机器人半径 (m)
    mass: float = 1e-18               # 质量 (kg)
    charge: float = 1e-12            # 电荷量 (C)
    magnetic_moment: float = 1e-15    # 磁矩 (A·m²)
    
    # 状态
    coupled_region_id: Optional[int] = None
    coupling_state: CouplingState = CouplingState.DECOUPLED
    energy: float = 100.0            # 能量水平 (0-100)
    
    # 邻居信息
    neighbors: List[int] = field(default_factory=list)
    coupling_strength: float = 0.0   # 当前耦合强度

@dataclass
class ControlRegion:
    """控制区域定义"""
    id: int
    center: Vector2D
    radius: float                      # 区域半径
    field_type: FieldType
    field_strength: float = 1.0       # 场强系数
    frequency: float = 1000.0         # 驱动频率 (Hz)
    phase: float = 0.0                # 相位
    active: bool = True
    
    # 选择性参数
    selectivity_radius: float = 0.0  # 选择性作用半径 (0表示全覆盖)
    target_robots: List[int] = field(default_factory=list)  # 目标机器人ID列表

@dataclass
class CouplingLink:
    """机器人间的耦合连接"""
    robot_id_a: int
    robot_id_b: int
    strength: float = 0.0             # 耦合强度 [0,1]
    state: CouplingState = CouplingState.DECOUPLED
    distance: float = 0.0

# ============================================================
# 第二部分: 场耦合动力学模型
# ============================================================

class FieldCouplingModel:
    """
    场耦合动力学模型
    
    模拟纳米机器人在外加场作用下的动力学行为
    支持: 磁场、电场、声场、光场等多种驱动方式
    """
    
    def __init__(self, field_type: FieldType):
        self.field_type = field_type
        self.params = self._init_params()
    
    def _init_params(self) -> Dict:
        """初始化场参数"""
        params_dict = {
            FieldType.MAGNETIC: {
                'coefficient': 1e-12,      # 磁力系数
                'gradient': 100.0,         # 磁场梯度 (T/m)
                'decay_rate': 0.1,        # 距离衰减率
            },
            FieldType.ELECTRIC: {
                'coefficient': 8.99e9,    # 库仑常数
                'permittivity': 78.0,      # 相对介电常数 (水)
                'decay_rate': 0.15,
            },
            FieldType.ACOUSTIC: {
                'coefficient': 1e-9,       # 声辐射力系数
                'wavelength': 1e-3,        # 声波波长 (m)
                'decay_rate': 0.2,
            },
            FieldType.OPTICAL: {
                'coefficient': 1e-12,      # 光辐射压力系数
                'wavelength': 650e-9,       # 激光波长 (nm)
                'decay_rate': 0.05,
            },
            FieldType.CHEMICAL: {
                'diffusion_coeff': 1e-9,   # 扩散系数 (m²/s)
                'reaction_rate:': 0.5,     # 反应速率
                'decay_rate': 0.3,
            }
        }
        return params_dict.get(self.field_type, params_dict[FieldType.MAGNETIC])
    
    def compute_force(self, robot: Nanorobot, field_vector: Vector2D, 
                      distance: float) -> Vector2D:
        """
        计算场对纳米机器人的作用力
        
        Args:
            robot: 纳米机器人
            field_vector: 场向量 (方向和强度)
            distance: 到场源的距离
        
        Returns:
            作用力向量
        """
        params = self.params
        decay = np.exp(-params.get('decay_rate', 0.1) * distance)
        
        if self.field_type == FieldType.MAGNETIC:
            # 磁场力: F = ∇(m·B)
            force_mag = params['coefficient'] * params['gradient'] * \
                       robot.magnetic_moment * field_vector.norm() * decay
            return field_vector.normalize() * force_mag
        
        elif self.field_type == FieldType.ELECTRIC:
            # 电场力: F = qE
            force_mag = robot.charge * field_vector.norm() * decay
            return field_vector.normalize() * force_mag
        
        elif self.field_type == FieldType.ACOUSTIC:
            # 声辐射力
            force_mag = params['coefficient'] * field_vector.norm()**2 * decay
            return field_vector.normalize() * force_mag
        
        elif self.field_type == FieldType.OPTICAL:
            # 光辐射压力
            force_mag = params['coefficient'] * field_vector.norm() * decay
            return field_vector.normalize() * force_mag
        
        else:
            return field_vector * decay
    
    def compute_coupling_force(self, robot_a: Nanorobot, robot_b: Nanorobot,
                               region_active: bool = True) -> Tuple[Vector2D, Vector2D]:
        """
        计算两个纳米机器人之间的耦合作用力
        
        Args:
            robot_a, robot_b: 两个纳米机器人
            region_active: 区域是否激活
        
        Returns:
            (作用于a的力, 作用于b的力)
        """
        # 相对位置和距离
        delta_pos = robot_b.position - robot_a.position
        distance = delta_pos.norm()
        
        if distance < 1e-10 or distance > 1e-6:  # 超出有效范围
            return Vector2D(), Vector2D()
        
        # 耦合强度随距离衰减 (Lennard-Jones-like)
        r0 = 100e-9  # 特征距离 100nm
        coupling_strength = 4 * ((r0/distance)**12 - (r0/distance)**6)
        coupling_strength = np.clip(coupling_strength, -1, 1)
        
        # 区域激活时的选择性耦合
        if region_active:
            coupling_strength = abs(coupling_strength)
        else:
            coupling_strength = 0
        
        # 耦合力
        direction = delta_pos.normalize()
        force_magnitude = coupling_strength * 1e-12  # 耦合力系数
        
        force_on_a = direction * force_magnitude
        force_on_b = direction * (-force_magnitude)
        
        return force_on_a, force_on_b

# ============================================================
# 第三部分: 区域选择性耦合控制器
# ============================================================

class RegionSelectiveController:
    """
    区域选择性耦合控制器
    
    核心创新点:
    1. 多区域独立控制
    2. 选择性耦合: 只有在特定区域内的机器人才会建立耦合
    3. 动态耦合强度调节
    4. 自适应场参数优化
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # 控制参数
        self.coupling_threshold = self.config.get('coupling_threshold', 0.3)
        self.decoupling_threshold = self.config.get('decoupling_threshold', 0.1)
        self.max_coupling_range = self.config.get('max_coupling_range', 200e-9)  # 200nm
        self.coherence_gain = self.config.get('coherence_gain', 0.5)
        
        # 区域管理
        self.regions: Dict[int, ControlRegion] = {}
        self.region_id_counter = 0
        
        # 耦合图 (邻接表)
        self.coupling_graph: Dict[int, List[int]] = {}
        
        # 性能指标
        self.metrics = {
            'coupling_efficiency': 0.0,
            'cluster_coherence': 0.0,
            'energy_consumption': 0.0,
            'control_error': 0.0
        }
    
    def add_region(self, center: Tuple[float, float], radius: float,
                   field_type: FieldType, **kwargs) -> int:
        """添加控制区域"""
        region = ControlRegion(
            id=self.region_id_counter,
            center=Vector2D(*center),
            radius=radius,
            field_type=field_type,
            **kwargs
        )
        self.regions[region.id] = region
        self.region_id_counter += 1
        return region.id
    
    def remove_region(self, region_id: int):
        """移除控制区域"""
        if region_id in self.regions:
            del self.regions[region_id]
    
    def get_robots_in_region(self, robots: List[Nanorobot], 
                              region_id: int) -> List[Nanorobot]:
        """获取指定区域内的机器人"""
        if region_id not in self.regions:
            return []
        
        region = self.regions[region_id]
        in_region = []
        
        for robot in robots:
            distance = (robot.position - region.center).norm()
            
            # 区域选择性判断
            if region.selectivity_radius > 0:
                # 精确选择模式
                if distance <= region.selectivity_radius:
                    in_region.append(robot)
            else:
                # 半径覆盖模式
                if distance <= region.radius:
                    in_region.append(robot)
        
        return in_region
    
    def compute_desired_coupling(self, robots: List[Nanorobot], 
                                  region_id: int) -> Dict[Tuple[int, int], float]:
        """
        计算区域内的期望耦合关系
        
        Returns:
            {(id_a, id_b): desired_strength}
        """
        if region_id not in self.regions:
            return {}
        
        region = self.regions[region_id]
        robots_in_region = self.get_robots_in_region(robots, region_id)
        
        desired_couplings = {}
        
        for i, robot_a in enumerate(robots_in_region):
            for robot_b in robots_in_region[i+1:]:
                # 基于相对位置和区域场计算期望耦合
                delta_pos = robot_b.position - robot_a.position
                distance = delta_pos.norm()
                
                if distance < self.max_coupling_range and distance > 1e-10:
                    # 距离相关的耦合强度
                    dist_factor = 1 - (distance / self.max_coupling_range)
                    
                    # 区域场影响
                    field_influence = region.field_strength * \
                                     np.exp(-distance / region.radius)
                    
                    # 综合耦合强度
                    coupling_strength = dist_factor * field_influence
                    coupling_strength = np.clip(coupling_strength, 0, 1)
                    
                    desired_couplings[(robot_a.id, robot_b.id)] = coupling_strength
        
        return desired_couplings
    
    def update_coupling_graph(self, robots: List[Nanorobot], dt: float):
        """更新耦合图"""
        # 初始化
        for robot in robots:
            if robot.id not in self.coupling_graph:
                self.coupling_graph[robot.id] = []
        
        # 计算所有活跃区域的耦合
        all_couplings = {}
        
        for region_id, region in self.regions.items():
            if not region.active:
                continue
            
            desired = self.compute_desired_coupling(robots, region_id)
            all_couplings.update(desired)
        
        # 更新耦合图
        for (id_a, id_b), strength in all_couplings.items():
            # 耦合建立
            if strength > self.coupling_threshold:
                if id_b not in self.coupling_graph[id_a]:
                    self.coupling_graph[id_a].append(id_b)
                if id_a not in self.coupling_graph[id_b]:
                    self.coupling_graph[id_b].append(id_a)
            
            # 耦合解除
            elif strength < self.decoupling_threshold:
                if id_b in self.coupling_graph[id_a]:
                    self.coupling_graph[id_a].remove(id_b)
                if id_a in self.coupling_graph[id_b]:
                    self.coupling_graph[id_b].remove(id_a)
        
        # 更新机器人状态
        for robot in robots:
            robot.neighbors = self.coupling_graph.get(robot.id, [])
            robot.coupling_strength = sum(
                1 for n in robot.neighbors
            ) / max(len(robots), 1)
    
    def compute_control_input(self, robot: Nanorobot, all_robots: List[Nanorobot],
                               target_position: Optional[Vector2D] = None) -> Vector2D:
        """
        计算控制输入
        
        包含:
        1. 目标吸引 (如果指定了目标位置)
        2. 耦合协同 (与区域内邻居)
        3. 场驱动 (区域内场作用)
        """
        control_input = Vector2D()
        
        # 1. 目标吸引
        if target_position is not None:
            to_target = target_position - robot.position
            control_input = control_input + to_target * 0.5
        
        # 2. 耦合协同
        for neighbor_id in robot.neighbors:
            neighbor = next((r for r in all_robots if r.id == neighbor_id), None)
            if neighbor is not None:
                # 聚集力
                to_neighbor = neighbor.position - robot.position
                control_input = control_input + to_neighbor * self.coherence_gain
                
                # 速度对齐
                vel_diff = neighbor.velocity - robot.velocity
                control_input = control_input + vel_diff * 0.3
        
        # 3. 区域场驱动
        for region in self.regions.values():
            if not region.active:
                continue
            
            # 检查是否在区域内
            distance = (robot.position - region.center).norm()
            if distance <= region.radius:
                # 场方向 (基于相位)
                field_direction = Vector2D(
                    np.cos(region.phase),
                    np.sin(region.phase)
                )
                field_force = field_direction * region.field_strength
                control_input = control_input + field_force
        
        return control_input
    
    def compute_metrics(self, robots: List[Nanorobot]):
        """计算性能指标"""
        if not robots:
            return
        
        # 耦合效率
        total_links = sum(len(neighbors) for neighbors in self.coupling_graph.values())
        max_links = len(robots) * (len(robots) - 1) / 2
        self.metrics['coupling_efficiency'] = total_links / max_links if max_links > 0 else 0
        
        # 聚类一致性 (基于速度对齐)
        if len(robots) > 1:
            velocities = np.array([(r.velocity.x, r.velocity.y) for r in robots])
            mean_vel = velocities.mean(axis=0)
            coherence = 0
            for v in velocities:
                coherence += np.dot(v, mean_vel) / (np.linalg.norm(v) + 1e-10)
            self.metrics['cluster_coherence'] = coherence / len(robots)
        else:
            self.metrics['cluster_coherence'] = 1.0
        
        # 能量消耗 (基于总动能和耦合消耗)
        total_kinetic = sum(r.velocity.norm()**2 for r in robots)
        self.metrics['energy_consumption'] = total_kinetic * 1e6

# ============================================================
# 第四部分: 数值仿真引擎
# ============================================================

class NanorobotSimulator:
    """
    纳米机器人集群数值仿真引擎
    
    使用有限差分法求解动力学方程
    """
    
    def __init__(self, controller: RegionSelectiveController,
                 field_model: FieldCouplingModel):
        self.controller = controller
        self.field_model = field_model
        
        # 仿真参数
        self.dt = 1e-6           # 时间步长 (s)
        self.sim_time = 0.0      # 当前仿真时间
        self.max_time = 10.0     # 最大仿真时间
        
        # 环境参数
        self.viscosity = 1e-3   # 流体粘度 (Pa·s) - 水
        self.temperature = 310  # 体温 (K) - 人体环境
        self.brownian_noise = True
        
        # 纳米机器人
        self.robots: List[Nanorobot] = []
        
        # 历史数据
        self.history: List[Dict] = []
        self.history_interval = 100  # 记录间隔
    
    def initialize_robots(self, num_robots: int, 
                         bounds: Tuple[float, float, float, float],
                         distribution: str = 'random'):
        """初始化纳米机器人"""
        self.robots = []
        
        x_min, x_max, y_min, y_max = bounds
        
        for i in range(num_robots):
            if distribution == 'random':
                pos = Vector2D(
                    np.random.uniform(x_min, x_max),
                    np.random.uniform(y_min, y_max)
                )
            elif distribution == 'cluster':
                # 聚集分布
                center = Vector2D(
                    (x_min + x_max) / 2,
                    (y_min + y_max) / 2
                )
                pos = Vector2D(
                    center.x + np.random.normal(0, (x_max-x_min)/6),
                    center.y + np.random.normal(0, (y_max-y_min)/6)
                )
            elif distribution == 'grid':
                # 网格分布
                n_side = int(np.sqrt(num_robots))
                row = i // n_side
                col = i % n_side
                pos = Vector2D(
                    x_min + (col + 0.5) * (x_max - x_min) / n_side,
                    y_min + (row + 0.5) * (y_max - y_min) / n_side
                )
            else:
                pos = Vector2D(0, 0)
            
            robot = Nanorobot(
                id=i,
                position=pos,
                velocity=Vector2D(np.random.normal(0, 1e-7), np.random.normal(0, 1e-7))
            )
            self.robots.append(robot)
        
        # 初始化耦合图
        self.controller.coupling_graph = {i: [] for i in range(num_robots)}
    
    def compute_drag_force(self, robot: Nanorobot) -> Vector2D:
        """计算粘滞阻力 (Stokes drag)"""
        # F_drag = 6πμRv
        radius = robot.radius
        drag_coefficient = 6 * np.pi * self.viscosity * radius
        return robot.velocity * (-drag_coefficient)
    
    def compute_brownian_force(self, robot: Nanorobot) -> Vector2D:
        """计算布朗运动随机力"""
        if not self.brownian_noise:
            return Vector2D()
        
        # 热噪声: F = sqrt(2 * kB * T * drag_coeff / dt) * N(0,1)
        kB = 1.380649e-23  # 玻尔兹曼常数
        drag_coeff = 6 * np.pi * self.viscosity * robot.radius
        noise_std = np.sqrt(2 * kB * self.temperature * drag_coeff / self.dt)
        
        return Vector2D(
            np.random.normal(0, noise_std),
            np.random.normal(0, noise_std)
        )
    
    def compute_total_force(self, robot: Nanorobot, 
                            target_position: Optional[Vector2D] = None) -> Vector2D:
        """计算机器人受合力"""
        total_force = Vector2D()
        
        # 1. 控制输入力
        control_force = self.controller.compute_control_input(
            robot, self.robots, target_position
        ) * robot.mass * 1e6  # 增益
        total_force = total_force + control_force
        
        # 2. 机器人间耦合作用力
        for neighbor_id in robot.neighbors:
            neighbor = next((r for r in self.robots if r.id == neighbor_id), None)
            if neighbor is not None:
                force_a, force_b = self.field_model.compute_coupling_force(
                    robot, neighbor, 
                    region_active=(robot.coupled_region_id is not None)
                )
                total_force = total_force + force_a
        
        # 3. 粘滞阻力
        total_force = total_force + self.compute_drag_force(robot)
        
        # 4. 布朗运动
        total_force = total_force + self.compute_brownian_force(robot)
        
        return total_force
    
    def step(self, target_position: Optional[Vector2D] = None):
        """单步仿真"""
        # 更新耦合图
        self.controller.update_coupling_graph(self.robots, self.dt)
        
        # 计算每个机器人的力
        forces = []
        for robot in self.robots:
            force = self.compute_total_force(robot, target_position)
            forces.append(force)
        
        # 更新状态 (Euler方法)
        for i, robot in enumerate(self.robots):
            # 加速度 a = F/m
            robot.acceleration = forces[i] / robot.mass
            
            # 速度 v = v + a*dt
            robot.velocity = robot.velocity + robot.acceleration * self.dt
            
            # 位置 x = x + v*dt
            robot.position = robot.position + robot.velocity * self.dt
        
        # 更新仿真时间
        self.sim_time += self.dt
        
        # 记录历史
        if len(self.history) < self.sim_time / (self.dt * self.history_interval):
            self.record_state()
        
        # 更新性能指标
        self.controller.compute_metrics(self.robots)
    
    def record_state(self):
        """记录当前状态"""
        state = {
            'time': self.sim_time,
            'positions': [(r.position.x, r.position.y) for r in self.robots],
            'velocities': [(r.velocity.x, r.velocity.y) for r in self.robots],
            'coupling_graph': dict(self.controller.coupling_graph),
            'metrics': dict(self.controller.metrics)
        }
        self.history.append(state)
    
    def run(self, target_position: Optional[Vector2D] = None,
            progress_callback: Optional[Callable] = None):
        """运行仿真"""
        step_count = 0
        max_steps = int(self.max_time / self.dt)
        
        while self.sim_time < self.max_time:
            self.step(target_position)
            step_count += 1
            
            if progress_callback and step_count % 1000 == 0:
                progress_callback(self.sim_time / self.max_time)
        
        # 最终记录
        self.record_state()
        
        if progress_callback:
            progress_callback(1.0)
        
        return self.history
    
    def get_trajectory(self, robot_id: int) -> List[Tuple[float, float]]:
        """获取指定机器人的轨迹"""
        trajectory = []
        for state in self.history:
            pos = state['positions'][robot_id]
            trajectory.append(pos)
        return trajectory

# ============================================================
# 第五部分: 可视化模块
# ============================================================

class Visualizer:
    """
    可视化模块
    
    支持:
    - 机器人轨迹
    - 耦合连接
    - 控制区域
    - 实时动画
    """
    
    # 颜色方案
    COLORS = {
        'robot': '#00CED1',           # 青色
        'robot_coupled': '#FF6347',    # 番茄红
        'coupling': '#32CD32',         # 线绿色
        'region_active': '#4169E1',    # 皇家蓝
        'region_inactive': '#808080',  # 灰色
        'target': '#FFD700',           # 金色
        'trajectory': '#9370DB'        # 中紫色
    }
    
    def __init__(self, simulator: NanorobotSimulator):
        self.simulator = simulator
        self.fig_size = (12, 10)
        self.dpi = 100
    
    def plot_snapshot(self, time_index: int = -1, 
                      show_regions: bool = True,
                      show_couplings: bool = True,
                      show_trajectory: bool = True,
                      trajectory_length: int = 50):
        """绘制快照"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            from matplotlib.collections import LineCollection
        except ImportError:
            print("需要安装 matplotlib: pip install matplotlib")
            return None
        
        if not self.simulator.history:
            print("没有仿真数据")
            return None
        
        # 获取数据
        if time_index < 0:
            time_index = len(self.simulator.history) + time_index
        
        state = self.simulator.history[time_index]
        
        # 创建图形
        fig, ax = plt.subplots(figsize=self.fig_size, dpi=self.dpi)
        
        # 绘制控制区域
        if show_regions:
            for region_id, region in self.simulator.controller.regions.items():
                color = self.COLORS['region_active'] if region.active \
                       else self.COLORS['region_inactive']
                
                circle = patches.Circle(
                    (region.center.x * 1e6, region.center.y * 1e6),
                    region.radius * 1e6,
                    linewidth=2,
                    edgecolor=color,
                    facecolor=color,
                    alpha=0.15,
                    linestyle='--'
                )
                ax.add_patch(circle)
                
                # 区域标签
                ax.text(region.center.x * 1e6, region.center.y * 1e6,
                       f'R{region.id}',
                       ha='center', va='center',
                       fontsize=10, fontweight='bold',
                       color=color)
        
        # 绘制轨迹
        if show_trajectory and len(self.simulator.history) > 1:
            start_idx = max(0, time_index - trajectory_length)
            for robot in self.simulator.robots:
                traj = []
                for t in range(start_idx, time_index + 1):
                    pos = self.simulator.history[t]['positions'][robot.id]
                    traj.append((pos[0] * 1e6, pos[1] * 1e6))
                
                if len(traj) > 1:
                    ax.plot(*zip(*traj), 
                           color=self.COLORS['trajectory'],
                           alpha=0.3, linewidth=1)
        
        # 绘制耦合连接
        if show_couplings:
            coupling_graph = state['coupling_graph']
            for robot_id, neighbors in coupling_graph.items():
                pos_a = state['positions'][robot_id]
                for neighbor_id in neighbors:
                    if neighbor_id > robot_id:  # 避免重复
                        pos_b = state['positions'][neighbor_id]
                        ax.plot([pos_a[0]*1e6, pos_b[0]*1e6],
                               [pos_a[1]*1e6, pos_b[1]*1e6],
                               color=self.COLORS['coupling'],
                               alpha=0.5, linewidth=1.5)
        
        # 绘制机器人
        for robot in self.simulator.robots:
            pos = state['positions'][robot.id]
            coupled = len(robot.neighbors) > 0
            color = self.COLORS['robot_coupled'] if coupled else self.COLORS['robot']
            
            # 机器人 (放大显示)
            ax.scatter(pos[0]*1e6, pos[1]*1e6, 
                      c=color, s=100, zorder=5,
                      edgecolors='white', linewidths=1)
            
            # 速度箭头
            vel = state['velocities'][robot.id]
            if np.linalg.norm(vel) > 1e-9:
                ax.annotate('', 
                          xy=(pos[0]*1e6 + vel[0]*1e8, pos[1]*1e6 + vel[1]*1e8),
                          xytext=(pos[0]*1e6, pos[1]*1e6),
                          arrowprops=dict(arrowstyle='->', 
                                         color='gray',
                                         alpha=0.5,
                                         lw=1))
        
        # 图形设置
        ax.set_xlabel('X (μm)', fontsize=12)
        ax.set_ylabel('Y (μm)', fontsize=12)
        ax.set_title(f'纳米机器人集群状态 (t = {state["time"]*1000:.2f} ms)',
                    fontsize=14, fontweight='bold')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')
        
        # 图例
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', 
                  markerfacecolor=self.COLORS['robot'], markersize=10,
                  label='自由机器人'),
            Line2D([0], [0], marker='o', color='w',
                  markerfacecolor=self.COLORS['robot_coupled'], markersize=10,
                  label='耦合机器人'),
            Line2D([0], [0], color=self.COLORS['coupling'], 
                  linewidth=2, label='耦合连接'),
            patches.Patch(facecolor=self.COLORS['region_active'], 
                        alpha=0.3, label='控制区域')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        return fig
    
    def plot_metrics(self):
        """绘制性能指标"""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return None
        
        if not self.simulator.history:
            return None
        
        # 提取数据
        times = [s['time'] * 1000 for s in self.simulator.history]
        coupling_eff = [s['metrics']['coupling_efficiency'] for s in self.simulator.history]
        coherence = [s['metrics']['cluster_coherence'] for s in self.simulator.history]
        energy = [s['metrics']['energy_consumption'] for s in self.simulator.history]
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # 耦合效率
        axes[0, 0].plot(times, coupling_eff, 'b-', linewidth=2)
        axes[0, 0].set_xlabel('Time (ms)')
        axes[0, 0].set_ylabel('Coupling Efficiency')
        axes[0, 0].set_title('Coupling Efficiency Over Time')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 聚类一致性
        axes[0, 1].plot(times, coherence, 'g-', linewidth=2)
        axes[0, 1].set_xlabel('Time (ms)')
        axes[0, 1].set_ylabel('Cluster Coherence')
        axes[0, 1].set_title('Cluster Coherence Over Time')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 能量消耗
        axes[1, 0].plot(times, energy, 'r-', linewidth=2)
        axes[1, 0].set_xlabel('Time (ms)')
        axes[1, 0].set_ylabel('Energy Consumption')
        axes[1, 0].set_title('Energy Consumption Over Time')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 机器人数量变化
        num_coupled = []
        for s in self.simulator.history:
            coupled_count = sum(1 for neighbors in s['coupling_graph'].values() 
                               if len(neighbors) > 0)
            num_coupled.append(coupled_count)
        
        axes[1, 1].plot(times, num_coupled, 'm-', linewidth=2)
        axes[1, 1].set_xlabel('Time (ms)')
        axes[1, 1].set_ylabel('Number of Coupled Robots')
        axes[1, 1].set_title('Coupled Robots Over Time')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def animate(self, interval: int = 50, save_path: Optional[str] = None):
        """生成动画"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.animation as animation
        except ImportError:
            print("需要安装 matplotlib")
            return None
        
        fig, ax = plt.subplots(figsize=self.fig_size, dpi=self.dpi)
        
        def update(frame):
            ax.clear()
            
            # 使用 plot_snapshot 的逻辑
            state = self.simulator.history[frame]
            
            # 绘制区域
            for region_id, region in self.simulator.controller.regions.items():
                color = self.COLORS['region_active'] if region.active \
                       else self.COLORS['region_inactive']
                import matplotlib.patches as patches
                circle = patches.Circle(
                    (region.center.x * 1e6, region.center.y * 1e6),
                    region.radius * 1e6,
                    linewidth=2, edgecolor=color,
                    facecolor=color, alpha=0.15, linestyle='--'
                )
                ax.add_patch(circle)
            
            # 绘制耦合
            coupling_graph = state['coupling_graph']
            for robot_id, neighbors in coupling_graph.items():
                pos_a = state['positions'][robot_id]
                for neighbor_id in neighbors:
                    if neighbor_id > robot_id:
                        pos_b = state['positions'][neighbor_id]
                        ax.plot([pos_a[0]*1e6, pos_b[0]*1e6],
                               [pos_a[1]*1e6, pos_b[1]*1e6],
                               color=self.COLORS['coupling'],
                               alpha=0.5, linewidth=1.5)
            
            # 绘制机器人
            for robot in self.simulator.robots:
                pos = state['positions'][robot.id]
                coupled = len(robot.neighbors) > 0
                color = self.COLORS['robot_coupled'] if coupled else self.COLORS['robot']
                ax.scatter(pos[0]*1e6, pos[1]*1e6,
                          c=color, s=100, zorder=5,
                          edgecolors='white', linewidths=1)
            
            ax.set_xlim(-2, 12)
            ax.set_ylim(-2, 12)
            ax.set_xlabel('X (μm)')
            ax.set_ylabel('Y (μm)')
            ax.set_title(f't = {state["time"]*1000:.2f} ms')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
        
        anim = animation.FuncAnimation(
            fig, update, 
            frames=len(self.simulator.history),
            interval=interval
        )
        
        if save_path:
            anim.save(save_path, writer='pillow', fps=20)
        
        return fig, anim


# ============================================================
# 第六部分: 主程序入口
# ============================================================

def create_demo_system():
    """创建演示系统"""
    
    print("=" * 60)
    print("纳米机器人集群区域选择性耦合控制系统")
    print("Region-Selective Coupling Control System for Nanorobot Swarm")
    print("=" * 60)
    
    # 1. 初始化控制器
    controller_config = {
        'coupling_threshold': 0.3,
        'decoupling_threshold': 0.1,
        'max_coupling_range': 150e-9,
        'coherence_gain': 0.5
    }
    controller = RegionSelectiveController(controller_config)
    
    # 2. 初始化场模型
    field_model = FieldCouplingModel(FieldType.MAGNETIC)
    
    # 3. 创建仿真器
    simulator = NanorobotSimulator(controller, field_model)
    
    # 4. 设置仿真参数
    simulator.dt = 1e-6
    simulator.max_time = 5.0
    simulator.brownian_noise = True
    
    # 5. 初始化纳米机器人 (20个，随机分布)
    simulator.initialize_robots(
        num_robots=20,
        bounds=(0, 10e-6, 0, 10e-6),
        distribution='random'
    )
    
    # 6. 添加控制区域
    # 区域1: 左侧聚集区
    controller.add_region(
        center=(3e-6, 5e-6),
        radius=3e-6,
        field_type=FieldType.MAGNETIC,
        field_strength=0.8,
        phase=0,
        active=True
    )
    
    # 区域2: 右侧目标区
    controller.add_region(
        center=(7e-6, 5e-6),
        radius=2.5e-6,
        field_type=FieldType.MAGNETIC,
        field_strength=1.0,
        phase=np.pi/2,
        active=True
    )
    
    # 7. 设置目标位置 (引导机器人集群移动)
    target = Vector2D(7e-6, 5e-6)
    
    print(f"\n仿真配置:")
    print(f"  - 纳米机器人数量: {len(simulator.robots)}")
    print(f"  - 时间步长: {simulator.dt * 1e6:.1f} μs")
    print(f"  - 最大仿真时间: {simulator.max_time * 1000:.1f} ms")
    print(f"  - 控制区域数量: {len(controller.regions)}")
    print(f"  - 布朗噪声: {simulator.brownian_noise}")
    
    # 8. 运行仿真
    print("\n开始仿真...")
    
    def progress(percent):
        if percent % 0.2 < 0.02:
            print(f"  进度: {percent*100:.0f}%")
    
    history = simulator.run(target_position=target)
    
    print(f"\n仿真完成! 共记录 {len(history)} 个时间点")
    
    # 9. 显示最终性能指标
    print("\n最终性能指标:")
    for key, value in controller.metrics.items():
        print(f"  - {key}: {value:.4f}")
    
    return simulator, controller, field_model


def run_custom_simulation(num_robots: int = 50,
                          num_regions: int = 3,
                          field_type: FieldType = FieldType.MAGNETIC,
                          sim_time: float = 10.0,
                          target_pos: Optional[Tuple[float, float]] = None):
    """运行自定义仿真"""
    
    # 控制器
    controller = RegionSelectiveController({
        'coupling_threshold': 0.25,
        'decoupling_threshold': 0.08,
        'max_coupling_range': 200e-9,
        'coherence_gain': 0.6
    })
    
    # 场模型
    field_model = FieldCouplingModel(field_type)
    
    # 仿真器
    simulator = NanorobotSimulator(controller, field_model)
    simulator.dt = 5e-7
    simulator.max_time = sim_time
    
    # 初始化机器人
    simulator.initialize_robots(
        num_robots=num_robots,
        bounds=(0, 20e-6, 0, 20e-6),
        distribution='cluster'
    )
    
    # 添加区域
    region_centers = [
        (5e-6, 10e-6),
        (10e-6, 10e-6),
        (15e-6, 10e-6)
    ]
    
    for i in range(min(num_regions, 3)):
        controller.add_region(
            center=region_centers[i],
            radius=4e-6,
            field_type=field_type,
            field_strength=0.8 + i * 0.2,
            phase=i * np.pi / 3,
            active=True
        )
    
    # 目标位置
    target = Vector2D(*target_pos) if target_pos else Vector2D(15e-6, 10e-6)
    
    # 运行
    print(f"运行仿真: {num_robots} 机器人, {num_regions} 区域, {sim_time}s")
    simulator.run(target_position=target)
    
    return simulator


# ============================================================
# 示例运行
# ============================================================

if __name__ == "__main__":
    # 创建并运行演示
    simulator, controller, field_model = create_demo_system()
    
    # 可视化
    viz = Visualizer(simulator)
    
    print("\n生成可视化...")
    
    # 绘制快照
    fig1 = viz.plot_snapshot(
        time_index=-1,
        show_regions=True,
        show_couplings=True,
        show_trajectory=True
    )
    
    # 绘制性能指标
    fig2 = viz.plot_metrics()
    
    print("\n可用的可视化方法:")
    print("  - viz.plot_snapshot(): 绘制当前状态快照")
    print("  - viz.plot_metrics(): 绘制性能指标曲线")
    print("  - viz.animate(): 生成动画 (需要安装 matplotlib)")
    
    # 显示图形
    try:
        import matplotlib.pyplot as plt
        plt.show()
    except:
        print("提示: 运行在交互环境查看图形，或保存为文件")
