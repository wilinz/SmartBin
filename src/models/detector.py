#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
垃圾检测模块
实时垃圾识别和分类
"""

import cv2
import numpy as np
import time
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

# 修复PyTorch 2.6权重加载问题
import torch
if hasattr(torch, 'serialization'):
    # 为PyTorch 2.6添加安全全局变量
    try:
        torch.serialization.add_safe_globals(['ultralytics.nn.tasks.DetectionModel'])
    except:
        pass

# 全局修复torch.load函数
original_torch_load = torch.load
def patched_torch_load(*args, **kwargs):
    # 强制设置weights_only=False
    kwargs.pop('weights_only', None)  # 移除可能存在的weights_only参数
    return original_torch_load(*args, weights_only=False, **kwargs)

torch.load = patched_torch_load

# 设置环境变量
os.environ['TORCH_WEIGHTS_ONLY'] = 'False'

from ultralytics import YOLO

from ..utils.config_loader import config_loader
from ..utils.image_utils import ImageProcessor
from ..utils.math_utils import MathUtils


class GarbageDetector:
    """垃圾检测器"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.config = config_loader.get_model_config()
        self.system_config = config_loader.get_system_config()
        
        self.model = None
        self.class_names = self.config.get('classes', {}).get('names', [])
        self.class_categories = self.config.get('classes', {}).get('categories', {})
        
        # 检测参数
        self.confidence_threshold = self.config.get('model', {}).get('confidence_threshold', 0.25)
        self.iou_threshold = self.config.get('model', {}).get('iou_threshold', 0.45)
        self.max_detections = self.config.get('model', {}).get('max_detections', 300)
        
        # 性能监控
        self.frame_times = []
        self.detection_history = []
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 加载模型 - 如果没有指定路径，使用默认模型路径
        if model_path:
            self.load_model(model_path)
        else:
            # 尝试加载默认模型路径
            default_path = config_loader.get_default_model_path()
            if Path(default_path).exists():
                self.load_model(default_path)
            else:
                self.logger.warning(f"默认模型文件不存在: {default_path}")
    
    def load_model(self, model_path: str):
        """
        加载检测模型
        
        Args:
            model_path: 模型文件路径
        """
        try:
            self.model = YOLO(model_path)
            self.logger.info(f"成功加载检测模型: {model_path}")
            
            # 预热模型
            self._warmup_model()
            
        except Exception as e:
            self.logger.error(f"加载检测模型失败: {e}")
            raise
    
    def _warmup_model(self):
        """预热模型以提高推理速度"""
        if self.model is None:
            return
        
        try:
            # 创建一个dummy图像进行预热
            dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model(dummy_image, verbose=False)
            self.logger.info("模型预热完成")
        except Exception as e:
            self.logger.warning(f"模型预热失败: {e}")
    
    def detect(self, 
               image: np.ndarray,
               conf_threshold: Optional[float] = None,
               iou_threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        检测图像中的垃圾
        
        Args:
            image: 输入图像 (BGR格式)
            conf_threshold: 置信度阈值
            iou_threshold: IoU阈值
        
        Returns:
            检测结果字典
        """
        if self.model is None:
            raise ValueError("模型未加载，请先加载模型")
        
        start_time = time.time()
        
        # 使用配置的阈值或传入的阈值
        conf_thresh = conf_threshold or self.confidence_threshold
        iou_thresh = iou_threshold or self.iou_threshold
        
        try:
            # 执行检测
            results = self.model(
                image,
                conf=conf_thresh,
                iou=iou_thresh,
                max_det=self.max_detections,
                verbose=False
            )
            
            # 解析检测结果
            detection_result = self._parse_results(results[0], image.shape)
            
            # 记录检测时间
            detection_time = time.time() - start_time
            self.frame_times.append(time.time())
            
            # 保持frame_times列表长度
            if len(self.frame_times) > 30:
                self.frame_times = self.frame_times[-30:]
            
            # 计算FPS
            fps = MathUtils.calculate_fps(self.frame_times)
            
            detection_result.update({
                'detection_time': detection_time,
                'fps': fps,
                'image_shape': image.shape
            })
            
            # 记录检测历史
            self.detection_history.append({
                'timestamp': time.time(),
                'detections': len(detection_result['detections']),
                'categories': detection_result['category_counts']
            })
            
            return detection_result
            
        except Exception as e:
            self.logger.error(f"检测失败: {e}")
            raise
    
    def _parse_results(self, result, image_shape: Tuple[int, int, int]) -> Dict[str, Any]:
        """
        解析YOLOv8检测结果
        
        Args:
            result: YOLOv8检测结果
            image_shape: 图像形状 (H, W, C)
        
        Returns:
            解析后的检测结果
        """
        detections = []
        category_counts = {category: 0 for category in self.class_categories.keys()}
        category_counts['unknown'] = 0
        
        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes.xyxy.cpu().numpy()  # 边界框坐标
            scores = result.boxes.conf.cpu().numpy()  # 置信度
            classes = result.boxes.cls.cpu().numpy().astype(int)  # 类别ID
            
            for i in range(len(boxes)):
                class_id = classes[i]
                if class_id < len(self.class_names):
                    class_name = self.class_names[class_id]
                else:
                    class_name = 'unknown'
                
                # 获取垃圾类别
                garbage_category = self._get_garbage_category(class_name)
                
                detection = {
                    'id': i,
                    'class_id': int(class_id),
                    'class_name': class_name,
                    'category': garbage_category,
                    'confidence': float(scores[i]),
                    'bbox': {
                        'x1': float(boxes[i][0]),
                        'y1': float(boxes[i][1]),
                        'x2': float(boxes[i][2]),
                        'y2': float(boxes[i][3])
                    },
                    'center': MathUtils.box_center(boxes[i].tolist()),
                    'area': MathUtils.box_area(boxes[i].tolist())
                }
                
                detections.append(detection)
                category_counts[garbage_category] += 1
        
        return {
            'detections': detections,
            'total_detections': len(detections),
            'category_counts': category_counts,
            'class_distribution': self._get_class_distribution(detections)
        }
    
    def _get_garbage_category(self, class_name: str) -> str:
        """
        获取垃圾类别
        
        Args:
            class_name: 类别名称
        
        Returns:
            垃圾类别 ('organic', 'recyclable', 'other', 'unknown')
        """
        for category, classes in self.class_categories.items():
            if class_name in classes:
                return category
        return 'unknown'
    
    def _get_class_distribution(self, detections: List[Dict]) -> Dict[str, int]:
        """获取类别分布统计"""
        distribution = {}
        for detection in detections:
            class_name = detection['class_name']
            distribution[class_name] = distribution.get(class_name, 0) + 1
        return distribution
    
    def detect_and_draw(self, 
                       image: np.ndarray,
                       draw_boxes: bool = True,
                       draw_labels: bool = True,
                       draw_confidence: bool = True) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        检测并在图像上绘制结果
        
        Args:
            image: 输入图像
            draw_boxes: 是否绘制边界框
            draw_labels: 是否绘制标签
            draw_confidence: 是否显示置信度
        
        Returns:
            (绘制了检测结果的图像, 检测结果字典)
        """
        # 执行检测
        results = self.detect(image)
        
        # 绘制结果
        result_image = image.copy()
        
        if draw_boxes and results['detections']:
            boxes = []
            labels = []
            scores = []
            colors = []
            
            # 定义类别颜色
            category_colors = {
                'organic': (0, 255, 0),      # 绿色
                'recyclable': (255, 0, 0),   # 蓝色
                'other': (0, 0, 255),        # 红色
                'unknown': (128, 128, 128)   # 灰色
            }
            
            for detection in results['detections']:
                bbox = detection['bbox']
                boxes.append([bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']])
                
                # 构建标签
                label_parts = []
                if draw_labels:
                    label_parts.append(detection['class_name'])
                if draw_confidence:
                    label_parts.append(f"{detection['confidence']:.2f}")
                
                labels.append(' '.join(label_parts))
                scores.append(detection['confidence'])
                colors.append(category_colors.get(detection['category'], (255, 255, 255)))
            
            # 绘制边界框
            result_image = ImageProcessor.draw_bounding_boxes(
                result_image, boxes, labels, scores, colors
            )
        
        # 绘制统计信息
        if results['total_detections'] > 0:
            self._draw_statistics(result_image, results)
        
        return result_image, results
    
    def _draw_statistics(self, image: np.ndarray, results: Dict[str, Any]):
        """在图像上绘制统计信息"""
        # 在图像左上角绘制FPS和检测统计
        y_offset = 30
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        color = (255, 255, 255)
        thickness = 2
        
        # FPS
        fps_text = f"FPS: {results.get('fps', 0):.1f}"
        cv2.putText(image, fps_text, (10, y_offset), font, font_scale, color, thickness)
        y_offset += 25
        
        # 总检测数
        total_text = f"Total: {results['total_detections']}"
        cv2.putText(image, total_text, (10, y_offset), font, font_scale, color, thickness)
        y_offset += 25
        
        # 各类别统计
        for category, count in results['category_counts'].items():
            if count > 0:
                category_text = f"{category}: {count}"
                cv2.putText(image, category_text, (10, y_offset), font, font_scale, color, thickness)
                y_offset += 20
    
    def get_detection_statistics(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        if not self.detection_history:
            return {"message": "暂无检测历史"}
        
        recent_history = self.detection_history[-100:]  # 最近100次检测
        
        total_detections = sum([h['detections'] for h in recent_history])
        avg_detections = total_detections / len(recent_history) if recent_history else 0
        
        # 统计各类别总数
        category_totals = {}
        for history in recent_history:
            for category, count in history['categories'].items():
                category_totals[category] = category_totals.get(category, 0) + count
        
        return {
            'total_frames_processed': len(recent_history),
            'total_detections': total_detections,
            'average_detections_per_frame': avg_detections,
            'category_totals': category_totals,
            'current_fps': MathUtils.calculate_fps(self.frame_times),
            'model_loaded': self.model is not None
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.frame_times = []
        self.detection_history = []
        self.logger.info("检测统计信息已重置")
    
    def set_confidence_threshold(self, threshold: float):
        """设置置信度阈值"""
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            self.logger.info(f"置信度阈值已设置为: {threshold}")
        else:
            raise ValueError("置信度阈值必须在0.0到1.0之间")
    
    def set_iou_threshold(self, threshold: float):
        """设置IoU阈值"""
        if 0.0 <= threshold <= 1.0:
            self.iou_threshold = threshold
            self.logger.info(f"IoU阈值已设置为: {threshold}")
        else:
            raise ValueError("IoU阈值必须在0.0到1.0之间")


def create_detector(model_path: Optional[str] = None) -> GarbageDetector:
    """创建垃圾检测器实例"""
    return GarbageDetector(model_path) 