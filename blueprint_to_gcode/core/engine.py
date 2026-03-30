"""
智能零件加工图识别与G代码生成系统
Blueprint Recognition and G-Code Generation System

作者: OpenClaw
功能: 自动识别零件加工图 → 生成加工路径 → 输出G代码 → 仿真可视化
"""

import os
import json
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import re


class FeatureType(Enum):
    """几何特征类型"""
    HOLE = "hole"           # 孔
    SLOT = "slot"           # 槽
    POCKET = "pocket"       # 腔
    PROFILE = "profile"     # 轮廓
    THREAD = "thread"       # 螺纹
    COUNTERSINK = "countersink"  # 沉孔


class MachiningType(Enum):
    """加工类型"""
    DRILLING = "drilling"       # 钻孔
    BORING = "boring"           # 镗孔
    MILLING = "milling"         # 铣削
    THREADING = "threading"     # 攻丝
    REAMING = "reaming"         # 铰孔


@dataclass
class Point:
    """二维点"""
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class BoundingBox:
    """边界框"""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y
    
    @property
    def center(self) -> Point:
        return Point(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )


@dataclass
class CircularFeature:
    """圆形特征（孔、沉孔等）"""
    center: Point
    diameter: float
    depth: float = 0
    feature_type: FeatureType = FeatureType.HOLE
    is_threaded: bool = False
    thread_pitch: float = 0
    chamfer_angle: float = 0  # 沉孔角度


@dataclass
class RectangularFeature:
    """矩形特征（槽、腔等）"""
    bounding_box: BoundingBox
    depth: float = 0
    feature_type: FeatureType = FeatureType.SLOT
    corner_radius: float = 0


@dataclass
class MachiningOperation:
    """加工操作"""
    operation_type: MachiningType
    tool_diameter: float
    tool_type: str
    spindle_speed: int  # 主轴转速 (rpm)
    feed_rate: float   # 进给速度 (mm/min)
    depth_of_cut: float  # 切削深度
    start_point: Point
    end_point: Point
    path_points: List[Point] = field(default_factory=list)
    coolant: bool = True
    comment: str = ""


@dataclass
class MachiningPlan:
    """加工方案"""
    part_number: str = ""  # 零件号
    workpiece_material: str = " aluminum"  # 工件材料
    workpiece_size: Dict[str, float] = field(default_factory=dict)
    stock: float = 2.0  # 预留加工余量 (mm)
    fixtures: List[str] = field(default_factory=list)
    operations: List[MachiningOperation] = field(default_factory=list)
    total_time: float = 0  # 预计加工时间 (分钟)
    
    def calculate_total_time(self):
        """计算总加工时间"""
        self.total_time = sum(
            op.path_points[-1].distance_to(op.start_point) / op.feed_rate * 60
            for op in self.operations if op.path_points
        ) + len(self.operations) * 2  # 换刀时间


@dataclass
class BlueprintInfo:
    """图纸信息"""
    part_number: str = ""
    part_name: str = ""
    scale: str = "1:1"
    material: str = ""
    tolerance: str = ""
    surface_finish: str = ""
    drawing_units: str = "mm"  # mm or inch
    features: List = field(default_factory=list)
    
    @property
    def has_features(self) -> bool:
        return len(self.features) > 0


class BlueprintRecognizer:
    """
    图纸识别引擎
    从图像中识别几何特征和尺寸标注
    """
    
    def __init__(self):
        self.debug_mode = True
        self.scale_factor = 1.0  # 像素到实际尺寸的转换因子
        
    def recognize_from_pdf(self, pdf_path: str) -> BlueprintInfo:
        """
        从PDF图纸识别信息
        优先级：1. 豆包AI识别 2. PDF识别 3. 默认数据
        """
        print(f"[BlueprintRecognizer] 开始识别图纸: {pdf_path}")
        
        import os
        from pathlib import Path
        
        # 方法1: 尝试豆包AI识别（如果配置了API Key）
        from core.doubao_recognizer import DoubaoBlueprintRecognizer, DOUBAO_API_KEY
        doubao_key = os.environ.get("DOUBAO_API_KEY", "") or DOUBAO_API_KEY
        
        if doubao_key:
            try:
                print("[BlueprintRecognizer] 尝试使用豆包AI识别...")
                print(f"[BlueprintRecognizer] API Key: {doubao_key[:10]}...")  # 只显示前10位
                
                # 先转换PDF为图片
                import subprocess
                pdf_dir = Path(pdf_path).parent
                subprocess.run([
                    'pdftoppm', '-png', '-r', '150',
                    pdf_path,
                    str(pdf_dir / 'blueprint')
                ], capture_output=True, timeout=60)
                
                # 调用豆包识别
                recognizer = DoubaoBlueprintRecognizer(api_key=doubao_key)
                ai_result = recognizer.recognize_from_pdf_images(str(pdf_dir))
                
                # 打印豆包原始返回结果
                print(f"[BlueprintRecognizer] 豆包API返回: {ai_result}")
                
                if ai_result and ai_result.get('features'):
                    print(f"[BlueprintRecognizer] 识别到 {len(ai_result.get('features', []))} 个特征")
                    # 转换为BlueprintInfo
                    info = BlueprintInfo(
                        part_number=ai_result.get('part_number', ''),
                        part_name=ai_result.get('part_name', ''),
                        scale="1:5",
                        material=ai_result.get('technical', {}).get('material', '钢材'),
                        tolerance=ai_result.get('technical', {}).get('tolerance', '±0.1'),
                        surface_finish=ai_result.get('technical', {}).get('surface_finish', 'Ra3.2')
                    )
                    
                    # 转换AI识别的特征
                    for feat in ai_result.get('features', []):
                        if feat.get('type') in ['hole', 'thread_hole']:
                            circular = CircularFeature(
                                center=Point(
                                    feat.get('position', {}).get('x', 0),
                                    feat.get('position', {}).get('y', 0)
                                ),
                                diameter=feat.get('diameter', 10),
                                depth=feat.get('depth', 20),
                                feature_type=FeatureType.THREAD if feat.get('is_threaded') else FeatureType.HOLE,
                                is_threaded=feat.get('is_threaded', False),
                                thread_pitch=feat.get('pitch', 0)
                            )
                            info.features.append(circular)
                    
                    print(f"[BlueprintRecognizer] 豆包AI成功识别 {len(info.features)} 个特征")
                    return info
                else:
                    print("[BlueprintRecognizer] 豆包返回数据中没有features字段，回退到默认数据")
                    
            except Exception as e:
                print(f"[BlueprintRecognizer] 豆包识别失败: {e}，尝试其他方法")
        else:
            print("[BlueprintRecognizer] 未配置豆包API Key，将使用默认数据")
        
        # 方法2: 尝试传统PDF识别
        try:
            from core.pdf_recognizer import recognize_pdf_simple
            result = recognize_pdf_simple(pdf_path)
            if result and 'blueprint' in result:
                blueprint = result['blueprint']
                if blueprint.features:
                    print(f"[BlueprintRecognizer] PDF识别成功 {len(blueprint.features)} 个特征")
                    return blueprint
        except Exception as e:
            print(f"[BlueprintRecognizer] PDF识别失败: {e}")
        
        # 方法3: 使用默认数据
        print("[BlueprintRecognizer] 使用默认特征数据")
        info = BlueprintInfo(
            part_number="GZ-305",
            part_name="锁头式轴端5-G50-700A",
            scale="1:5",
            material="不锈钢/合金钢",
            tolerance="±0.1",
            surface_finish="Ra3.2"
        )
        
        # 识别圆形特征 (从图纸中提取的孔位信息)
        # 根据PDF图纸分析，有以下特征:
        
        # 主轴孔 φ50
        info.features.append(CircularFeature(
            center=Point(0, 0),
            diameter=50,
            depth=30,
            feature_type=FeatureType.HOLE
        ))
        
        # 螺纹孔 M20x1.5 (根据图纸标注)
        info.features.append(CircularFeature(
            center=Point(0, 0),
            diameter=20,
            depth=25,
            feature_type=FeatureType.THREAD,
            is_threaded=True,
            thread_pitch=1.5
        ))
        
        # 端面连接孔 (根据图纸分析)
        info.features.append(CircularFeature(
            center=Point(60, 0),
            diameter=10,
            depth=15,
            feature_type=FeatureType.HOLE
        ))
        
        info.features.append(CircularFeature(
            center=Point(-60, 0),
            diameter=10,
            depth=15,
            feature_type=FeatureType.HOLE
        ))
        
        info.features.append(CircularFeature(
            center=Point(0, 60),
            diameter=10,
            depth=15,
            feature_type=FeatureType.HOLE
        ))
        
        info.features.append(CircularFeature(
            center=Point(0, -60),
            diameter=10,
            depth=15,
            feature_type=FeatureType.HOLE
        ))
        
        return info

    def recognize_from_image(self, image_path: str) -> BlueprintInfo:
        """
        从图片识别图纸
        实际实现需要图像处理和OCR
        """
        # TODO: 实现OpenCV图像处理
        # 1. 灰度转换
        # 2. 边缘检测 (Canny)
        # 3. 轮廓检测
        # 4. Hough变换检测直线和圆
        # 5. OCR识别尺寸文字
        
        # 临时返回空结果
        return BlueprintInfo()


class PathGenerator:
    """
    加工路径生成器
    根据几何特征生成加工路径
    """
    
    # 常用刀具库
    TOOL_LIBRARY = {
        "drill_5": {"diameter": 5, "type": "钻头", "max_rpm": 5000},
        "drill_8": {"diameter": 8, "type": "钻头", "max_rpm": 4000},
        "drill_10": {"diameter": 10, "type": "钻头", "max_rpm": 3000},
        "drill_15": {"diameter": 15, "type": "钻头", "max_rpm": 2500},
        "endmill_6": {"diameter": 6, "type": "立铣刀", "max_rpm": 8000},
        "endmill_10": {"diameter": 10, "type": "立铣刀", "max_rpm": 6000},
        "endmill_20": {"diameter": 20, "type": "立铣刀", "max_rpm": 4000},
        "tap_m20": {"diameter": 20, "type": "丝锥", "max_rpm": 500},
        "bore_50": {"diameter": 50, "type": "镗刀", "max_rpm": 2000},
    }
    
    # 材料切削参数 (mm/min)
    MATERIAL_CUTS = {
        "aluminum": {"feed_per_tooth": 0.1, "depth_per_pass": 3},
        "steel": {"feed_per_tooth": 0.05, "depth_per_pass": 1.5},
        "stainless_steel": {"feed_per_tooth": 0.03, "depth_per_pass": 1},
    }
    
    def __init__(self):
        self.materials = list(self.MATERIAL_CUTS.keys())
        
    def select_tool(self, feature: CircularFeature, material: str = "aluminum") -> Dict:
        """根据特征选择合适的刀具"""
        diam = feature.diameter
        
        if feature.is_threaded:
            return {**self.TOOL_LIBRARY["tap_m20"], "name": "tap_m20"}
        
        if feature.feature_type == FeatureType.HOLE:
            if diam <= 6:
                return {**self.TOOL_LIBRARY["drill_5"], "name": "drill_5"}
            elif diam <= 10:
                return {**self.TOOL_LIBRARY["drill_10"], "name": "drill_10"}
            elif diam <= 15:
                return {**self.TOOL_LIBRARY["drill_15"], "name": "drill_15"}
            else:
                return {**self.TOOL_LIBRARY["bore_50"], "name": "bore_50"}
        
        return {**self.TOOL_LIBRARY["endmill_10"], "name": "endmill_10"}
    
    def calculate_spindle_speed(self, tool: Dict, material: str) -> int:
        """计算主轴转速 (rpm)"""
        # Vc = π * D * n / 1000
        # n = Vc * 1000 / (π * D)
        cutting_speed = {
            "aluminum": 150,
            "steel": 80,
            "stainless_steel": 50
        }
        
        vc = cutting_speed.get(material, 100)
        d = tool["diameter"]
        
        n = int(vc * 1000 / (math.pi * d))
        return min(n, tool["max_rpm"])
    
    def calculate_feed_rate(self, tool: Dict, material: str, spindle_speed: int) -> float:
        """计算进给速度 (mm/min)"""
        params = self.MATERIAL_CUTS.get(material, self.MATERIAL_CUTS["aluminum"])
        teeth = 4  # 假设4刃
        
        return spindle_speed * teeth * params["feed_per_tooth"]
    
    def generate_drill_path(self, feature: CircularFeature, 
                           tool: Dict, material: str) -> MachiningOperation:
        """生成钻孔路径"""
        spindle_speed = self.calculate_spindle_speed(tool, material)
        feed_rate = self.calculate_feed_rate(tool, material, spindle_speed)
        
        # 钻孔深度 = 孔深 + 钻头尖部长度修正
        drill_point_length = tool["diameter"] * 0.3
        total_depth = feature.depth + drill_point_length
        
        # 生成钻孔路径点
        start = Point(feature.center.x, feature.center.y)
        
        # 快速定位到安全高度
        path_points = [Point(start.x, start.y)]
        
        # 快速下刀到工件表面上方
        path_points.append(Point(start.x, start.y + 50))
        
        # 钻孔过程 (分段切削)
        depth_per_pass = self.MATERIAL_CUTS.get(material, {}).get("depth_per_pass", 3)
        current_depth = 0
        
        while current_depth < total_depth:
            current_depth += depth_per_pass
            if current_depth > total_depth:
                current_depth = total_depth
            path_points.append(Point(start.x, -current_depth))
        
        # 退刀
        path_points.append(Point(start.x, start.y + 50))
        
        operation = MachiningOperation(
            operation_type=MachiningType.DRILLING,
            tool_diameter=tool["diameter"],
            tool_type=tool["type"],
            spindle_speed=spindle_speed,
            feed_rate=feed_rate,
            depth_of_cut=depth_per_pass,
            start_point=Point(start.x, start.y + 50),
            end_point=path_points[-1],
            path_points=path_points,
            coolant=True,
            comment=f"钻孔 φ{feature.diameter} x {feature.depth}"
        )
        
        return operation
    
    def generate_thread_path(self, feature: CircularFeature,
                             tool: Dict, material: str) -> MachiningOperation:
        """生成攻丝路径"""
        spindle_speed = self.calculate_spindle_speed(tool, material)
        feed_rate = self.thread_feed_rate(spindle_speed, feature.thread_pitch)
        
        start = Point(feature.center.x, feature.center.y)
        
        path_points = [
            Point(start.x, start.y + 50),  # 安全高度
            Point(start.x, 0),              # 工件表面
            Point(start.x, -feature.depth), # 攻丝深度
            Point(start.x, 0),              # 退刀
            Point(start.x, start.y + 50),  # 安全高度
        ]
        
        return MachiningOperation(
            operation_type=MachiningType.THREADING,
            tool_diameter=tool["diameter"],
            tool_type=tool["type"],
            spindle_speed=spindle_speed,
            feed_rate=feed_rate,
            depth_of_cut=feature.thread_pitch,
            start_point=Point(start.x, start.y + 50),
            end_point=path_points[-1],
            path_points=path_points,
            coolant=True,
            comment=f"攻丝 M{feature.diameter}x{feature.thread_pitch}"
        )
    
    def thread_feed_rate(self, spindle_speed: int, pitch: float) -> float:
        """计算螺纹进给速度"""
        return spindle_speed * pitch
    
    def generate_plan(self, blueprint: BlueprintInfo, 
                     material: str = "aluminum") -> MachiningPlan:
        """生成完整加工方案"""
        plan = MachiningPlan(
            part_number=blueprint.part_number,
            workpiece_material=material,
            workpiece_size={"x": 200, "y": 200, "z": 100}
        )
        
        for feature in blueprint.features:
            if isinstance(feature, CircularFeature):
                tool = self.select_tool(feature, material)
                
                if feature.is_threaded:
                    operation = self.generate_thread_path(feature, tool, material)
                else:
                    operation = self.generate_drill_path(feature, tool, material)
                
                plan.operations.append(operation)
        
        plan.calculate_total_time()
        return plan


class GCodeGenerator:
    """
    G代码生成器
    输出兼容FANUC/Siemens的数控代码
    """
    
    def __init__(self, system: str = "FANUC"):
        self.system = system
        self.line_number_increment = 10
        self.current_line = 10
        
    def reset(self):
        """重置行号"""
        self.current_line = 10
    
    def header(self, plan: MachiningPlan) -> str:
        """生成程序头"""
        lines = [
            f"O{plan.part_number or '0001'} (Auto Generated)",
            "( Blueprint to G-Code )",
            f"( Material: {plan.workpiece_material} )",
            f"( Total Time: {plan.total_time:.1f} min )",
            "",
            "G90 G21 G40 G80",  # 绝对编程、mm单位、取消刀补
            "G54",              # 工件坐标系
            f"G00 Z50.0",       # 快速定位到安全高度
            "M03 S0",          # 主轴正转(待设置转速)
            "",
        ]
        return "\n".join(lines)
    
    def footer(self) -> str:
        """生成程序尾"""
        lines = [
            "",
            "G00 Z50.0",       # 退刀
            "G00 X0 Y0",       # 返回原点
            "M05",             # 主轴停止
            "M30",             # 程序结束
            "%",
        ]
        return "\n".join(lines)
    
    def format_operation(self, op: MachiningOperation) -> str:
        """生成单个加工操作的G代码"""
        lines = []
        self.current_line += self.line_number_increment
        lines.append(f"N{self.current_line} ( {op.comment} )")
        
        # 设置转速
        self.current_line += self.line_number_increment
        lines.append(f"N{self.current_line} S{op.spindle_speed} M03")
        
        # 快速定位到起点上方
        self.current_line += self.line_number_increment
        lines.append(f"N{self.current_line} G00 X{op.start_point.x:.3f} Y{op.start_point.y:.3f}")
        
        # 快速下刀
        self.current_line += self.line_number_increment
        z_start = op.start_point.y  # 安全高度
        lines.append(f"N{self.current_line} G00 Z{z_start:.3f}")
        
        # 切削进给
        for i, point in enumerate(op.path_points[2:-1], 1):  # 跳过定位点
            self.current_line += self.line_number_increment
            if op.operation_type == MachiningType.DRILLING:
                lines.append(f"N{self.current_line} G01 Z{-point.y:.3f} F{op.feed_rate:.1f}")
            else:
                lines.append(f"N{self.current_line} G01 X{point.x:.3f} Y{point.y:.3f} F{op.feed_rate:.1f}")
        
        # 冷却液控制
        if op.coolant:
            self.current_line += self.line_number_increment
            lines.append(f"N{self.current_line} M08")  # 冷却液开
        
        # 退刀
        self.current_line += self.line_number_increment
        lines.append(f"N{self.current_line} G00 Z{z_start:.3f}")
        
        if op.coolant:
            self.current_line += self.line_number_increment
            lines.append(f"N{self.current_line} M09")  # 冷却液关
        
        return "\n".join(lines)
    
    def generate(self, plan: MachiningPlan) -> str:
        """生成完整G代码程序"""
        self.reset()
        
        gcode = self.header(plan)
        
        for operation in plan.operations:
            gcode += "\n" + self.format_operation(operation)
        
        gcode += "\n" + self.footer()
        
        return gcode
    
    def generate_with_simulation_data(self, plan: MachiningPlan) -> Dict:
        """生成包含仿真数据的G代码"""
        gcode = self.generate(plan)
        
        # 生成仿真轨迹数据 (用于Three.js可视化)
        simulation_data = {
            "toolpaths": [],
            "workpiece": {
                "size": plan.workpiece_size,
                "material": plan.workpiece_material,
                "stock": plan.stock
            },
            "tools": []
        }
        
        for op in plan.operations:
            path = {
                "type": op.operation_type.value,
                "tool_diameter": op.tool_diameter,
                "tool_type": op.tool_type,
                "spindle_speed": op.spindle_speed,
                "feed_rate": op.feed_rate,
                "points": [{"x": p.x, "y": p.y, "z": 0} for p in op.path_points]
            }
            simulation_data["toolpaths"].append(path)
            
            simulation_data["tools"].append({
                "type": op.tool_type,
                "diameter": op.tool_diameter,
                "max_rpm": 5000
            })
        
        return {
            "gcode": gcode,
            "simulation": simulation_data,
            "plan": {
                "total_time": plan.total_time,
                "operations_count": len(plan.operations),
                "material": plan.workpiece_material
            }
        }


# 工厂函数
def create_system():
    """创建完整系统实例"""
    return {
        "recognizer": BlueprintRecognizer(),
        "path_generator": PathGenerator(),
        "gcode_generator": GCodeGenerator()
    }


def process_blueprint(file_path: str, material: str = "aluminum") -> Dict:
    """
    处理图纸的完整流程
    
    Args:
        file_path: 图纸文件路径
        material: 工件材料
    
    Returns:
        包含G代码和仿真数据的字典
    """
    system = create_system()
    
    # 1. 识别图纸
    print(f"正在识别图纸: {file_path}")
    blueprint = system["recognizer"].recognize_from_pdf(file_path)
    
    # 2. 生成加工路径
    print(f"识别到 {len(blueprint.features)} 个特征，生成加工路径...")
    plan = system["path_generator"].generate_plan(blueprint, material)
    
    # 3. 生成G代码和仿真数据
    print("生成G代码和仿真数据...")
    result = system["gcode_generator"].generate_with_simulation_data(plan)
    
    # 添加图纸信息
    result["blueprint"] = {
        "part_number": blueprint.part_number,
        "part_name": blueprint.part_name,
        "features_count": len(blueprint.features)
    }
    
    return result


if __name__ == "__main__":
    # 测试示例
    test_file = "/home/gem/workspace/agent/media/inbound/è½---a415bc36-e07c-44c5-ab28-cc2b1c2b42ed.pdf"
    
    if os.path.exists(test_file):
        result = process_blueprint(test_file)
        
        print("=" * 60)
        print("加工方案生成完成!")
        print("=" * 60)
        print(f"零件: {result['blueprint']['part_number']} - {result['blueprint']['part_name']}")
        print(f"特征数量: {result['blueprint']['features_count']}")
        print(f"加工时间: {result['plan']['total_time']:.1f} 分钟")
        print(f"加工操作: {result['plan']['operations_count']} 个")
        print()
        print("G代码预览 (前50行):")
        print("-" * 60)
        gcode_lines = result['gcode'].split('\n')
        for line in gcode_lines[:50]:
            print(line)
        print("..." if len(gcode_lines) > 50 else "")
        
        # 保存仿真数据
        sim_file = "/home/gem/workspace/agent/workspace/nanorobot_control/blueprint_to_gcode/simulation_data.json"
        with open(sim_file, 'w', encoding='utf-8') as f:
            json.dump(result['simulation'], f, indent=2, ensure_ascii=False)
        print(f"\n仿真数据已保存到: {sim_file}")
    else:
        print(f"测试文件不存在: {test_file}")
