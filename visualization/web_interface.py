#!/usr/bin/env python3
"""
纳米机器人集群控制仿真系统 - Web可视化界面
============================================

基于Flask和WebSocket的实时仿真监控界面

作者: OpenClaw
"""

import json
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

# ============================================================
# 仿真数据生成器
# ============================================================

class RealtimeSimulator:
    """实时仿真数据生成器"""
    
    def __init__(self):
        self.running = False
        self.data = {
            'robots': [],
            'regions': [],
            'metrics': {
                'coupling_efficiency': 0.0,
                'coherence': 0.0,
                'energy': 0.0
            }
        }
        self.time = 0.0
        self.thread: Optional[threading.Thread] = None
    
    def start(self, num_robots: int = 30):
        """启动仿真"""
        self.running = True
        self.time = 0.0
        
        # 初始化机器人
        self.data['robots'] = []
        for i in range(num_robots):
            angle = np.random.uniform(0, 2 * np.pi)
            r = np.random.uniform(0, 5)
            self.data['robots'].append({
                'id': i,
                'x': 5 + r * np.cos(angle),
                'y': 5 + r * np.sin(angle),
                'vx': np.random.randn() * 0.1,
                'vy': np.random.randn() * 0.1,
                'coupled': False
            })
        
        # 初始化区域
        self.data['regions'] = [
            {'id': 0, 'x': 3, 'y': 5, 'radius': 2.5, 'active': True},
            {'id': 1, 'x': 7, 'y': 5, 'radius': 2.5, 'active': True},
            {'id': 2, 'x': 10, 'y': 5, 'radius': 2.0, 'active': False}
        ]
        
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
    
    def _run(self):
        """仿真循环"""
        dt = 0.05
        
        while self.running:
            self.time += dt
            
            # 更新机器人位置
            for robot in self.data['robots']:
                # 简单运动模型
                robot['x'] += robot['vx'] * dt
                robot['y'] += robot['vy'] * dt
                
                # 边界反弹
                if robot['x'] < 0 or robot['x'] > 15:
                    robot['vx'] *= -0.8
                    robot['x'] = np.clip(robot['x'], 0, 15)
                if robot['y'] < 0 or robot['y'] > 10:
                    robot['vy'] *= -0.8
                    robot['y'] = np.clip(robot['y'], 0, 10)
                
                # 添加一些随机性
                robot['vx'] += np.random.randn() * 0.02
                robot['vy'] += np.random.randn() * 0.02
                
                # 摩擦
                robot['vx'] *= 0.98
                robot['vy'] *= 0.98
            
            # 更新耦合状态
            coupled_count = 0
            for robot in self.data['robots']:
                # 检查是否在活跃区域内
                in_active_region = False
                for region in self.data['regions']:
                    if region['active']:
                        dx = robot['x'] - region['x']
                        dy = robot['y'] - region['y']
                        if (dx**2 + dy**2) ** 0.5 < region['radius']:
                            in_active_region = True
                            break
                
                robot['coupled'] = in_active_region
                if in_active_region:
                    coupled_count += 1
            
            # 更新指标
            self.data['metrics'] = {
                'coupling_efficiency': coupled_count / len(self.data['robots']),
                'coherence': 0.7 + 0.3 * np.sin(self.time * 0.5),
                'energy': 0.3 + 0.2 * np.random.random(),
                'time': self.time
            }
            
            time.sleep(0.05)
    
    def stop(self):
        """停止仿真"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return self.data.copy()


# 全局仿真器实例
_simulator = RealtimeSimulator()


# ============================================================
# HTTP服务器
# ============================================================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>纳米机器人集群控制系统</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #eee;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 30px;
        }
        
        header h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        header p {
            color: #888;
            margin-top: 10px;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        
        .panel {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .panel h2 {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #00d4ff;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }
        
        #simulation-canvas {
            width: 100%;
            height: 450px;
            background: #0a0a15;
            border-radius: 10px;
            cursor: crosshair;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            color: white;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #00ff88, #00cc6a);
            color: #1a1a2e;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff4757, #cc3344);
            color: white;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .metric-card {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #00d4ff;
        }
        
        .metric-label {
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .region-control {
            margin-top: 15px;
        }
        
        .region-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            margin-bottom: 10px;
        }
        
        .toggle-switch {
            position: relative;
            width: 50px;
            height: 26px;
        }
        
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #333;
            transition: .4s;
            border-radius: 26px;
        }
        
        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        
        input:checked + .slider {
            background-color: #00d4ff;
        }
        
        input:checked + .slider:before {
            transform: translateX(24px);
        }
        
        .slider.round {
            border-radius: 34px;
        }
        
        .slider.round:before {
            border-radius: 50%;
        }
        
        .stats-row {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.3em;
            color: #00ff88;
        }
        
        .stat-label {
            font-size: 0.8em;
            color: #888;
        }
        
        .legend {
            display: flex;
            gap: 20px;
            margin-top: 15px;
            justify-content: center;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .status-running {
            background: #00ff88;
            animation: pulse 1.5s infinite;
        }
        
        .status-stopped {
            background: #ff4757;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🦞 纳米机器人集群区域选择性耦合控制系统</h1>
            <p>Nanorobot Swarm Region-Selective Coupling Control System</p>
        </header>
        
        <div class="main-grid">
            <div class="panel">
                <h2>
                    <span id="status-indicator" class="status-indicator status-stopped"></span>
                    实时仿真视图
                </h2>
                <canvas id="simulation-canvas"></canvas>
                
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-dot" style="background: #00d4ff;"></div>
                        <span>自由机器人</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-dot" style="background: #ff6347;"></div>
                        <span>耦合机器人</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-dot" style="background: #32cd32; border-radius: 0; width: 20px; height: 3px;"></div>
                        <span>耦合连接</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-dot" style="background: rgba(65, 105, 225, 0.3); border: 2px solid #4169e1;"></div>
                        <span>控制区域</span>
                    </div>
                </div>
                
                <div class="controls">
                    <button class="btn-primary" onclick="startSimulation()" id="btn-start">
                        ▶ 开始仿真
                    </button>
                    <button class="btn-danger" onclick="stopSimulation()" id="btn-stop" disabled>
                        ⏹ 停止
                    </button>
                    <button class="btn-success" onclick="resetSimulation()">
                        🔄 重置
                    </button>
                </div>
            </div>
            
            <div class="right-column">
                <div class="panel">
                    <h2>📊 性能指标</h2>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value" id="metric-coupling">0.00</div>
                            <div class="metric-label">耦合效率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value" id="metric-coherence">0.00</div>
                            <div class="metric-label">聚类一致性</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value" id="metric-energy">0.00</div>
                            <div class="metric-label">能量消耗</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value" id="metric-time">0.0s</div>
                            <div class="metric-label">仿真时间</div>
                        </div>
                    </div>
                    
                    <div class="stats-row">
                        <div class="stat-item">
                            <div class="stat-value" id="stat-robots">0</div>
                            <div class="stat-label">总机器人</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="stat-coupled">0</div>
                            <div class="stat-label">已耦合</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="stat-regions">3</div>
                            <div class="stat-label">控制区域</div>
                        </div>
                    </div>
                </div>
                
                <div class="panel" style="margin-top: 20px;">
                    <h2>🎯 区域控制</h2>
                    <div class="region-control" id="region-list">
                        <!-- 区域列表 -->
                    </div>
                </div>
                
                <div class="panel" style="margin-top: 20px;">
                    <h2>⚙️ 仿真参数</h2>
                    <div style="margin-top: 15px;">
                        <label style="display: block; margin-bottom: 8px;">机器人数量: <span id="robot-count">30</span></label>
                        <input type="range" min="10" max="100" value="30" 
                               onchange="updateRobotCount(this.value)"
                               style="width: 100%;">
                    </div>
                    <div style="margin-top: 15px;">
                        <label style="display: block; margin-bottom: 8px;">时间流速: <span id="speed-value">1.0x</span></label>
                        <input type="range" min="0.1" max="3" step="0.1" value="1"
                               onchange="updateSpeed(this.value)"
                               style="width: 100%;">
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 仿真状态
        let isRunning = false;
        let animationId = null;
        let lastUpdate = 0;
        let robotCount = 30;
        let speedMultiplier = 1.0;
        
        // 画布上下文
        const canvas = document.getElementById('simulation-canvas');
        const ctx = canvas.getContext('2d');
        
        // 设置画布大小
        function resizeCanvas() {
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width * window.devicePixelRatio;
            canvas.height = rect.height * window.devicePixelRatio;
            ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        }
        
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        
        // 颜色定义
        const colors = {
            robot: '#00d4ff',
            robotCoupled: '#ff6347',
            coupling: '#32cd32',
            region: 'rgba(65, 105, 225, 0.15)',
            regionBorder: '#4169e1',
            background: '#0a0a15',
            grid: 'rgba(255, 255, 255, 0.05)'
        };
        
        // 坐标转换
        const plotArea = { x: 30, y: 30, width: 0, height: 0 };
        
        function toCanvas(x, y) {
            return {
                x: plotArea.x + x / 15 * plotArea.width,
                y: plotArea.y + y / 10 * (plotArea.height - 60) + 30
            };
        }
        
        // 绘制函数
        function draw(data) {
            const width = canvas.width / window.devicePixelRatio;
            const height = canvas.height / window.devicePixelRatio;
            
            plotArea.width = width - 60;
            plotArea.height = height - 60;
            
            // 清空画布
            ctx.fillStyle = colors.background;
            ctx.fillRect(0, 0, width, height);
            
            // 绘制网格
            ctx.strokeStyle = colors.grid;
            ctx.lineWidth = 1;
            for (let x = 0; x <= 15; x += 3) {
                const p = toCanvas(x, 0);
                ctx.beginPath();
                ctx.moveTo(p.x, toCanvas(0, 0).y);
                ctx.lineTo(p.x, toCanvas(0, 10).y);
                ctx.stroke();
            }
            for (let y = 0; y <= 10; y += 2) {
                const p = toCanvas(0, y);
                ctx.beginPath();
                ctx.moveTo(toCanvas(0, 0).x, p.y);
                ctx.lineTo(toCanvas(15, 0).x, p.y);
                ctx.stroke();
            }
            
            // 绘制区域
            if (data.regions) {
                data.regions.forEach(region => {
                    const center = toCanvas(region.x, region.y);
                    const radius = (region.radius / 15) * plotArea.width;
                    
                    ctx.beginPath();
                    ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
                    ctx.fillStyle = region.active ? colors.region : 'rgba(128, 128, 128, 0.1)';
                    ctx.fill();
                    ctx.strokeStyle = region.active ? colors.regionBorder : '#808080';
                    ctx.lineWidth = 2;
                    ctx.setLineDash([5, 5]);
                    ctx.stroke();
                    ctx.setLineDash([]);
                    
                    // 区域标签
                    ctx.fillStyle = region.active ? colors.regionBorder : '#808080';
                    ctx.font = 'bold 14px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.fillText(`R${region.id}`, center.x, center.y);
                });
            }
            
            // 绘制耦合连接
            if (data.robots) {
                ctx.strokeStyle = colors.coupling;
                ctx.lineWidth = 1;
                data.robots.forEach(robot => {
                    if (robot.coupled) {
                        data.robots.forEach(other => {
                            if (other.coupled && other.id > robot.id) {
                                const p1 = toCanvas(robot.x, robot.y);
                                const p2 = toCanvas(other.x, other.y);
                                const dist = Math.sqrt((robot.x - other.x)**2 + (robot.y - other.y)**2);
                                if (dist < 3) {
                                    ctx.beginPath();
                                    ctx.moveTo(p1.x, p1.y);
                                    ctx.lineTo(p2.x, p2.y);
                                    ctx.stroke();
                                }
                            }
                        });
                    }
                });
            }
            
            // 绘制机器人
            if (data.robots) {
                data.robots.forEach(robot => {
                    const pos = toCanvas(robot.x, robot.y);
                    
                    ctx.beginPath();
                    ctx.arc(pos.x, pos.y, robot.coupled ? 8 : 6, 0, Math.PI * 2);
                    ctx.fillStyle = robot.coupled ? colors.robotCoupled : colors.robot;
                    ctx.fill();
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    
                    // 速度箭头
                    if (Math.abs(robot.vx) > 0.01 || Math.abs(robot.vy) > 0.01) {
                        ctx.beginPath();
                        ctx.moveTo(pos.x, pos.y);
                        ctx.lineTo(pos.x + robot.vx * 30, pos.y + robot.vy * 30);
                        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }
                });
            }
            
            // 更新指标显示
            if (data.metrics) {
                document.getElementById('metric-coupling').textContent = 
                    data.metrics.coupling_efficiency.toFixed(2);
                document.getElementById('metric-coherence').textContent = 
                    data.metrics.coherence.toFixed(2);
                document.getElementById('metric-energy').textContent = 
                    data.metrics.energy.toFixed(2);
                document.getElementById('metric-time').textContent = 
                    (data.metrics.time || 0).toFixed(1) + 's';
                
                const coupled = data.robots ? data.robots.filter(r => r.coupled).length : 0;
                document.getElementById('stat-coupled').textContent = coupled;
                document.getElementById('stat-robots').textContent = data.robots ? data.robots.length : 0;
            }
        }
        
        // API调用
        async function fetchState() {
            try {
                const response = await fetch('/api/state');
                return await response.json();
            } catch (e) {
                return { robots: [], regions: [], metrics: {} };
            }
        }
        
        async function startSim() {
            await fetch('/api/start?count=' + robotCount);
            isRunning = true;
            updateButtons();
            animate();
        }
        
        async function stopSim() {
            await fetch('/api/stop');
            isRunning = false;
            updateButtons();
            if (animationId) {
                cancelAnimationFrame(animationId);
            }
        }
        
        async function resetSim() {
            await fetch('/api/reset');
            isRunning = false;
            updateButtons();
            if (animationId) {
                cancelAnimationFrame(animationId);
            }
            const data = await fetchState();
            draw(data);
        }
        
        function updateButtons() {
            document.getElementById('btn-start').disabled = isRunning;
            document.getElementById('btn-stop').disabled = !isRunning;
            const indicator = document.getElementById('status-indicator');
            indicator.className = 'status-indicator ' + (isRunning ? 'status-running' : 'status-stopped');
        }
        
        function animate(timestamp) {
            if (!isRunning) return;
            
            if (timestamp - lastUpdate > 50 / speedMultiplier) {
                fetchState().then(draw);
                lastUpdate = timestamp;
            }
            
            animationId = requestAnimationFrame(animate);
        }
        
        // 全局函数
        window.startSimulation = startSim;
        window.stopSimulation = stopSim;
        window.resetSimulation = resetSim;
        
        window.updateRobotCount = function(value) {
            robotCount = parseInt(value);
            document.getElementById('robot-count').textContent = value;
        };
        
        window.updateSpeed = function(value) {
            speedMultiplier = parseFloat(value);
            document.getElementById('speed-value').textContent = value + 'x';
        };
        
        // 初始化区域控制
        function initRegionControls() {
            const container = document.getElementById('region-list');
            const regions = [
                { id: 0, name: '区域 A (左)', active: true },
                { id: 1, name: '区域 B (中)', active: true },
                { id: 2, name: '区域 C (右)', active: false }
            ];
            
            container.innerHTML = regions.map(r => `
                <div class="region-item">
                    <span>${r.name}</span>
                    <label class="toggle-switch">
                        <input type="checkbox" ${r.active ? 'checked' : ''} 
                               onchange="toggleRegion(${r.id}, this.checked)">
                        <span class="slider round"></span>
                    </label>
                </div>
            `).join('');
        }
        
        window.toggleRegion = async function(id, active) {
            await fetch('/api/region/' + id + '/toggle?active=' + active);
        };
        
        // 初始化
        initRegionControls();
        fetchState().then(draw);
    </script>
</body>
</html>
'''


class RequestHandler(SimpleHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
        elif self.path.startswith('/api/'):
            self.handle_api()
        else:
            super().do_GET()
    
    def handle_api(self):
        """处理API请求"""
        global _simulator
        
        if self.path == '/api/state':
            # 获取状态
            data = _simulator.get_state()
            self.send_json(data)
        
        elif self.path.startswith('/api/start'):
            # 启动仿真
            import urllib.parse
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            count = int(params.get('count', [30])[0])
            _simulator.start(count)
            self.send_json({'status': 'started'})
        
        elif self.path == '/api/stop':
            # 停止仿真
            _simulator.stop()
            self.send_json({'status': 'stopped'})
        
        elif self.path == '/api/reset':
            # 重置
            _simulator.stop()
            _simulator = RealtimeSimulator()
            self.send_json({'status': 'reset'})
        
        elif self.path.startswith('/api/region/'):
            # 区域控制
            parts = self.path.split('/')
            if len(parts) >= 4 and parts[3] == 'toggle':
                region_id = int(parts[2])
                params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                active = params.get('active', ['false'])[0] == 'true'
                
                for region in _simulator.data['regions']:
                    if region['id'] == region_id:
                        region['active'] = active
                        break
                
                self.send_json({'status': 'ok'})
            else:
                self.send_json({'error': 'unknown command'})
        
        else:
            self.send_json({'error': 'not found'})
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def run_server(port=8080):
    """运行Web服务器"""
    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    print(f"🌐 纳米机器人控制系统已启动: http://localhost:{port}")
    print("按 Ctrl+C 停止服务器")
    server.serve_forever()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
