# Blueprint to G-Code System - 依赖安装脚本

## Python 依赖

```bash
pip install flask flask-cors werkzeug numpy scipy matplotlib opencv-python-headless pillow pdf2image pytesseract shapely ezdxf
```

## Tesseract OCR (用于图纸文字识别)

### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra libtesseract-dev
```

### macOS:
```bash
brew install tesseract tesseract-lang
```

### Windows:
下载并安装：https://github.com/UB-Mannheim/tesseract/wiki

## Docker 部署 (推荐)

### 1. 构建镜像
```bash
docker build -t blueprint-to-gcode .
```

### 2. 运行容器
```bash
docker run -d \
  --name blueprint-gcode \
  -p 5000:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/outputs:/app/outputs \
  blueprint-to-gcode
```

### 3. 使用 Docker Compose (推荐)
```bash
docker-compose up -d
```

## Nginx 反向代理配置

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # 大文件上传限制
    client_max_body_size 50M;
}
```

## 系统要求

- Python 3.8+
- 至少 2GB RAM
- 支持 PDF/DXF 解析的磁盘空间
- 可选：GPU 加速 (用于图像处理)

## 性能优化建议

1. **使用 Redis 缓存** - 减少重复计算
2. **Celery 任务队列** - 异步处理大文件
3. **Nginx 静态文件服务** - 提升前端加载速度
4. **数据库存储** - 持久化历史记录
