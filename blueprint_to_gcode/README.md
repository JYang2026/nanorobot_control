# 智能零件加工图识别与 G 代码生成系统

## 功能

- 从 PDF 图纸自动识别零件几何特征
- 生成数控加工路径
- 输出兼容 FANUC/Siemens 的 G 代码
- 3D 仿真可视化预览

## 使用方法

```python
from core.engine import process_blueprint

# 处理图纸文件
result = process_blueprint("blueprint.pdf", material="aluminum")

# 获取 G 代码
gcode = result['gcode']
print(gcode)
```

## API

```bash
# 启动 Web 服务
python3 api/app.py
```

访问 http://localhost:5000 查看界面。
