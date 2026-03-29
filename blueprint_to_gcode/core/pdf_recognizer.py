"""
PDF图纸识别模块
使用pdf2image + OpenCV + Tesseract OCR提取图纸信息
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re

# 尝试导入可选依赖
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class PDFBlueprintRecognizer:
    """PDF图纸识别器"""
    
    def __init__(self, dpi: int = 200):
        self.dpi = dpi
        self.scale_factor = 1.0  # 像素到毫米的转换因子
        
    def pdf_to_images(self, pdf_path: str) -> List[np.ndarray]:
        """将PDF转换为图像"""
        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("请安装 pdf2image: pip install pdf2image")
        
        # 转换PDF为图像列表
        images = convert_from_path(
            pdf_path,
            dpi=self.dpi,
            fmt='png',
            thread_count=2,
            poppler_path=None  # Windows可能需要指定poppler路径
        )
        
        # 转换为OpenCV格式
        cv_images = []
        for img in images:
            # PIL转numpy数组
            img_array = np.array(img)
            # PIL是RGB，OpenCV是BGR
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            cv_images.append(img_array)
        
        return cv_images
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理"""
        # 转为灰度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 高斯模糊去噪
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 自适应阈值二值化
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        return binary
    
    def detect_lines(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """检测直线（尺寸标注线）"""
        # 霍夫直线检测
        lines = cv2.HoughLinesP(
            image, 1, np.pi/180, threshold=100,
            minLineLength=50, maxLineGap=10
        )
        
        horizontal_lines = []
        vertical_lines = []
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                
                if angle < 20 or angle > 160:  # 水平线
                    horizontal_lines.append((x1, y1, x2, y2))
                elif 70 < angle < 110:  # 垂直线
                    vertical_lines.append((x1, y1, x2, y2))
        
        return np.array(horizontal_lines), np.array(vertical_lines)
    
    def detect_circles(self, image: np.ndarray) -> List[Tuple[int, int, int]]:
        """检测圆形（孔）"""
        circles = cv2.HoughCircles(
            image, cv2.HOUGH_GRADIENT, dp=1.2,
            minDist=50, param1=100, param2=30,
            minRadius=10, maxRadius=100
        )
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype(int)
            return [(int(c[0]), int(c[1]), int(c[2])) for c in circles]
        
        return []
    
    def extract_text_near_feature(self, image: np.ndarray, 
                                  feature_center: Tuple[int, int], 
                                  radius: int = 50) -> str:
        """提取特征附近的文字（尺寸标注）"""
        if not TESSERACT_AVAILABLE:
            return ""
        
        x, y = feature_center
        # 提取感兴趣区域
        x1 = max(0, x - radius)
        y1 = max(0, y - radius)
        x2 = min(image.shape[1], x + radius)
        y2 = min(image.shape[0], y + radius)
        
        roi = image[y1:y2, x1:x2]
        
        # OCR识别
        text = pytesseract.image_to_string(roi, config='--psm 6')
        
        # 清理文本
        text = re.sub(r'[^\w\.\-\+×φ]', '', text)
        
        return text.strip()
    
    def parse_dimension_text(self, text: str) -> Optional[float]:
        """解析尺寸文本（如 'φ50', '50', 'M20'）"""
        if not text:
            return None
        
        # 去除空格和特殊字符
        text = text.strip().replace(' ', '').replace('φ', '').replace('Φ', '')
        
        # 匹配数字
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if match:
            return float(match.group(1))
        
        return None
    
    def recognize_features(self, images: List[np.ndarray]) -> List[Dict]:
        """从图像序列识别特征"""
        all_features = []
        
        for img_idx, img in enumerate(images):
            print(f"处理第 {img_idx + 1} 页图纸...")
            
            # 预处理
            binary = self.preprocess_image(img)
            
            # 检测圆形特征（孔）
            circles = self.detect_circles(binary)
            
            for (cx, cy, r) in circles:
                # 计算直径（像素）
                diameter_px = r * 2
                
                # 转换为实际尺寸（需要校准，这里假设1像素=0.5mm）
                diameter_mm = diameter_px * 0.5
                
                # 提取附近文字
                text = self.extract_text_near_feature(img, (cx, cy))
                dimension = self.parse_dimension_text(text)
                
                if dimension:
                    diameter_mm = dimension
                
                feature = {
                    'type': 'hole',
                    'center': (cx, cy),
                    'radius_px': r,
                    'diameter_mm': diameter_mm,
                    'page': img_idx,
                    'text': text,
                    'is_threaded': 'M' in text or 'm' in text
                }
                all_features.append(feature)
        
        return all_features
    
    def recognize(self, pdf_path: str) -> Dict:
        """主识别函数"""
        print(f"开始识别PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"文件不存在: {pdf_path}")
        
        # 转换为图像
        print("正在转换PDF为图像...")
        images = self.pdf_to_images(pdf_path)
        print(f"共 {len(images)} 页")
        
        # 识别特征
        features = self.recognize_features(images)
        
        # 聚合结果
        result = {
            'total_pages': len(images),
            'total_features': len(features),
            'features': features,
            'image_dimensions': [(img.shape[1], img.shape[0]) for img in images]
        }
        
        return result


def recognize_pdf_simple(pdf_path: str) -> Dict:
    """
    简化的PDF识别接口
    返回与BlueprintRecognizer兼容的数据结构
    """
    recognizer = PDFBlueprintRecognizer()
    
    try:
        result = recognizer.recognize(pdf_path)
        
        # 转换为BlueprintInfo格式
        from core.engine import BlueprintInfo, CircularFeature, Point
        
        info = BlueprintInfo(
            part_number="PDF_" + Path(pdf_path).stem[:10],
            part_name="自动识别零件",
            scale="1:1",
            material="未知",
            tolerance="±0.1",
            surface_finish="Ra3.2"
        )
        
        # 转换特征
        for feat in result['features']:
            if feat['type'] == 'hole':
                circular = CircularFeature(
                    center=Point(feat['center'][0], feat['center'][1]),
                    diameter=feat['diameter_mm'],
                    depth=30,  # 默认深度
                    feature_type=FeatureType.HOLE if not feat.get('is_threaded') else FeatureType.THREAD,
                    is_threaded=feat.get('is_threaded', False)
                )
                info.features.append(circular)
        
        return {
            'blueprint': info,
            'raw_features': result['features'],
            'image_count': result['total_pages']
        }
        
    except Exception as e:
        print(f"PDF识别失败: {e}")
        # 返回空结果，使用默认数据
        from core.engine import BlueprintRecognizer
        fallback = BlueprintRecognizer()
        return {'blueprint': fallback.recognize_from_pdf(pdf_path)}


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        result = recognize_pdf_simple(pdf_file)
        
        print("\n识别结果:")
        print(f"特征数量: {len(result['blueprint'].features)}")
        for i, feat in enumerate(result['blueprint'].features, 1):
            print(f"  {i}. {feat.feature_type.value} - φ{feat.diameter}mm")
    else:
        print("用法: python pdf_recognizer.py <pdf文件路径>")
