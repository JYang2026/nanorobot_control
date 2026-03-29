"""
Blueprint to G-Code System - Flask API
后端服务接口
"""

import os
import sys
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging

# 导入核心引擎
from core.engine import process_blueprint, create_system

# 配置
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
ALLOWED_EXTENSIONS = {'pdf', 'dxf', 'dwg', 'png', 'jpg', 'jpeg', 'tiff'}

# 创建必要的目录
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# 配置日志
log_file = BASE_DIR / "api.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 配置
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['OUTPUT_FOLDER'] = str(OUTPUT_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 最大上传


def allowed_file(filename: str) -> bool:
    """检查文件扩展名"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_task_id() -> str:
    """生成任务ID"""
    return f"task_{uuid.uuid4().hex[:16]}_{int(time.time())}"


@app.route('/')
def index():
    """主页 - 返回静态文件"""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    上传图纸文件
    
    POST参数:
        file: 图纸文件 (PDF/DXF/DWG/Image)
        material: 材料类型 (可选，默认: aluminum)
        cnc_system: CNC系统类型 (可选，默认: FANUC)
    
    返回:
        JSON响应，包含任务ID和处理状态
    """
    # 检查文件是否存在
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型'}), 400
    
    # 获取参数
    material = request.form.get('material', 'aluminum')
    cnc_system = request.form.get('cnc_system', 'FANUC')
    
    try:
        # 保存文件
        task_id = generate_task_id()
        filename = secure_filename(f"{task_id}_{file.filename}")
        filepath = UPLOAD_FOLDER / filename
        file.save(filepath)
        
        logger.info(f"文件上传成功: {filename}, Task ID: {task_id}")
        
        # 处理图纸 (后台任务)
        # 实际生产环境应使用Celery等任务队列
        start_time = time.time()
        result = process_blueprint(str(filepath), material)
        processing_time = time.time() - start_time
        
        # 保存结果
        output_path = OUTPUT_FOLDER / f"{task_id}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # 保存G代码文件
        gcode_path = OUTPUT_FOLDER / f"{task_id}.nc"
        with open(gcode_path, 'w', encoding='utf-8') as f:
            f.write(result['gcode'])
        
        logger.info(f"处理完成: 耗时 {processing_time:.2f}秒")
        
        return jsonify({
            'task_id': task_id,
            'status': 'completed',
            'processing_time': processing_time,
            'blueprint': result['blueprint'],
            'plan': result['plan'],
            'gcode_url': f'/api/download/gcode/{task_id}',
            'simulation_url': f'/api/download/simulation/{task_id}'
        })
    
    except Exception as e:
        logger.error(f"处理失败: {str(e)}", exc_info=True)
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@app.route('/api/download/gcode/<task_id>', methods=['GET'])
def download_gcode(task_id: str):
    """下载G代码文件"""
    filepath = OUTPUT_FOLDER / f"{task_id}.nc"
    if not filepath.exists():
        return jsonify({'error': '文件不存在'}), 404
    
    return send_file(filepath, as_attachment=True, download_name=f"program_{task_id}.nc")


@app.route('/api/download/simulation/<task_id>', methods=['GET'])
def download_simulation(task_id: str):
    """下载仿真数据JSON"""
    filepath = OUTPUT_FOLDER / f"{task_id}.json"
    if not filepath.exists():
        return jsonify({'error': '文件不存在'}), 404
    
    return send_file(filepath, as_attachment=True, download_name=f"simulation_{task_id}.json")


@app.route('/api/simulation/<task_id>', methods=['GET'])
def get_simulation_data(task_id: str):
    """获取仿真数据 (JSON格式)"""
    filepath = OUTPUT_FOLDER / f"{task_id}.json"
    if not filepath.exists():
        return jsonify({'error': '仿真数据不存在'}), 404
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return jsonify(data)


@app.route('/api/preview/gcode/<task_id>', methods=['GET'])
def preview_gcode(task_id: str):
    """预览G代码 (前100行)"""
    filepath = OUTPUT_FOLDER / f"{task_id}.nc"
    if not filepath.exists():
        return jsonify({'error': 'G代码不存在'}), 404
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    preview_lines = [line.strip() for line in lines[:100] if line.strip()]
    
    return jsonify({
        'total_lines': len(lines),
        'preview': preview_lines
    })


@app.route('/api/task/list', methods=['GET'])
def list_tasks():
    """列出所有任务"""
    tasks = []
    for json_file in OUTPUT_FOLDER.glob("task_*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            task_id = json_file.stem
            tasks.append({
                'task_id': task_id,
                'created_at': datetime.fromtimestamp(json_file.stat().st_mtime).isoformat(),
                'status': 'completed',
                'blueprint': data.get('blueprint', {}),
                'plan': data.get('plan', {})
            })
        except Exception as e:
            logger.warning(f"读取任务失败 {json_file}: {e}")
    
    # 按创建时间倒序
    tasks.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify({'tasks': tasks[:20]})


@app.route('/api/system/info', methods=['GET'])
def system_info():
    """系统信息"""
    return jsonify({
        'name': 'Blueprint to G-Code System',
        'version': '1.0.0',
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'supported_materials': ['aluminum', 'steel', 'stainless_steel'],
        'supported_cnc_systems': ['FANUC', 'SIEMENS', 'MITSUBISHI'],
        'upload_limit': '50MB',
        'engine_version': '1.0.0'
    })


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '资源未找到'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500


if __name__ == '__main__':
    logger.info("启动 Blueprint to G-Code API 服务...")
    logger.info(f"上传目录: {UPLOAD_FOLDER}")
    logger.info(f"输出目录: {OUTPUT_FOLDER}")
    
    # 开发模式
    app.run(host='0.0.0.0', port=5000, debug=True)
    
    # 生产模式建议使用 Gunicorn:
    # gunicorn -w 4 -b 0.0.0.0:5000 api:app
