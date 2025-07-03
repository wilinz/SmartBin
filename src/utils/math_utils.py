#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数学计算工具
提供各种数学计算功能
"""

import math
import numpy as np
from typing import List, Tuple, Union


class MathUtils:
    """数学计算工具类"""
    
    @staticmethod
    def calculate_iou(box1: List[float], box2: List[float]) -> float:
        """
        计算两个边界框的IoU (Intersection over Union)
        
        Args:
            box1: 边界框1 [x1, y1, x2, y2]
            box2: 边界框2 [x1, y1, x2, y2]
        
        Returns:
            IoU值
        """
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # 计算交集区域
        x1_inter = max(x1_1, x1_2)
        y1_inter = max(y1_1, y1_2)
        x2_inter = min(x2_1, x2_2)
        y2_inter = min(y2_1, y2_2)
        
        # 检查是否有交集
        if x2_inter <= x1_inter or y2_inter <= y1_inter:
            return 0.0
        
        # 计算交集面积
        intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        # 计算并集面积
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        # 避免除零
        if union == 0:
            return 0.0
        
        return intersection / union
    
    @staticmethod
    def non_max_suppression(boxes: List[List[float]], 
                           scores: List[float],
                           score_threshold: float = 0.5,
                           iou_threshold: float = 0.4) -> List[int]:
        """
        非极大值抑制 (Non-Maximum Suppression)
        
        Args:
            boxes: 边界框列表
            scores: 置信度分数列表
            score_threshold: 置信度阈值
            iou_threshold: IoU阈值
        
        Returns:
            保留的边界框索引列表
        """
        if not boxes or not scores:
            return []
        
        # 过滤低置信度的框
        indices = [i for i, score in enumerate(scores) if score >= score_threshold]
        
        if not indices:
            return []
        
        # 按置信度降序排序
        indices.sort(key=lambda i: scores[i], reverse=True)
        
        keep = []
        while indices:
            # 取置信度最高的框
            current = indices.pop(0)
            keep.append(current)
            
            # 计算与其他框的IoU，移除重叠度高的框
            indices = [i for i in indices 
                      if MathUtils.calculate_iou(boxes[current], boxes[i]) <= iou_threshold]
        
        return keep
    
    @staticmethod
    def calculate_distance(point1: Tuple[float, float], 
                          point2: Tuple[float, float]) -> float:
        """
        计算两点间的欧几里得距离
        
        Args:
            point1: 点1坐标 (x, y)
            point2: 点2坐标 (x, y)
        
        Returns:
            距离值
        """
        x1, y1 = point1
        x2, y2 = point2
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    @staticmethod
    def calculate_angle(point1: Tuple[float, float],
                       point2: Tuple[float, float],
                       point3: Tuple[float, float]) -> float:
        """
        计算三点形成的角度
        
        Args:
            point1: 第一个点
            point2: 顶点
            point3: 第三个点
        
        Returns:
            角度值（弧度）
        """
        x1, y1 = point1
        x2, y2 = point2
        x3, y3 = point3
        
        # 计算向量
        vec1 = (x1 - x2, y1 - y2)
        vec2 = (x3 - x2, y3 - y2)
        
        # 计算点积和模长
        dot_product = vec1[0] * vec2[0] + vec1[1] * vec2[1]
        norm1 = math.sqrt(vec1[0] ** 2 + vec1[1] ** 2)
        norm2 = math.sqrt(vec2[0] ** 2 + vec2[1] ** 2)
        
        # 避免除零
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # 计算夹角
        cos_angle = dot_product / (norm1 * norm2)
        cos_angle = max(-1.0, min(1.0, cos_angle))  # 限制在[-1, 1]范围内
        
        return math.acos(cos_angle)
    
    @staticmethod
    def box_center(box: List[float]) -> Tuple[float, float]:
        """
        计算边界框的中心点
        
        Args:
            box: 边界框 [x1, y1, x2, y2]
        
        Returns:
            中心点坐标 (cx, cy)
        """
        x1, y1, x2, y2 = box
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    @staticmethod
    def box_area(box: List[float]) -> float:
        """
        计算边界框面积
        
        Args:
            box: 边界框 [x1, y1, x2, y2]
        
        Returns:
            面积值
        """
        x1, y1, x2, y2 = box
        return max(0, x2 - x1) * max(0, y2 - y1)
    
    @staticmethod
    def xywh_to_xyxy(box: List[float]) -> List[float]:
        """
        将YOLO格式的边界框转换为标准格式
        
        Args:
            box: YOLO格式边界框 [x_center, y_center, width, height]
        
        Returns:
            标准格式边界框 [x1, y1, x2, y2]
        """
        x_center, y_center, width, height = box
        x1 = x_center - width / 2
        y1 = y_center - height / 2
        x2 = x_center + width / 2
        y2 = y_center + height / 2
        return [x1, y1, x2, y2]
    
    @staticmethod
    def xyxy_to_xywh(box: List[float]) -> List[float]:
        """
        将标准格式的边界框转换为YOLO格式
        
        Args:
            box: 标准格式边界框 [x1, y1, x2, y2]
        
        Returns:
            YOLO格式边界框 [x_center, y_center, width, height]
        """
        x1, y1, x2, y2 = box
        x_center = (x1 + x2) / 2
        y_center = (y1 + y2) / 2
        width = x2 - x1
        height = y2 - y1
        return [x_center, y_center, width, height]
    
    @staticmethod
    def normalize_box(box: List[float], 
                     img_width: int, 
                     img_height: int) -> List[float]:
        """
        归一化边界框坐标
        
        Args:
            box: 边界框坐标
            img_width: 图像宽度
            img_height: 图像高度
        
        Returns:
            归一化的边界框坐标
        """
        return [
            box[0] / img_width,
            box[1] / img_height,
            box[2] / img_width,
            box[3] / img_height
        ]
    
    @staticmethod
    def denormalize_box(box: List[float],
                       img_width: int,
                       img_height: int) -> List[float]:
        """
        反归一化边界框坐标
        
        Args:
            box: 归一化的边界框坐标
            img_width: 图像宽度
            img_height: 图像高度
        
        Returns:
            实际的边界框坐标
        """
        return [
            box[0] * img_width,
            box[1] * img_height,
            box[2] * img_width,
            box[3] * img_height
        ]
    
    @staticmethod
    def smooth_coordinates(coords_history: List[Tuple[float, float]],
                          alpha: float = 0.8) -> Tuple[float, float]:
        """
        使用指数移动平均平滑坐标序列
        
        Args:
            coords_history: 历史坐标列表
            alpha: 平滑系数 (0-1)
        
        Returns:
            平滑后的坐标
        """
        if not coords_history:
            return (0.0, 0.0)
        
        if len(coords_history) == 1:
            return coords_history[0]
        
        smoothed_x, smoothed_y = coords_history[0]
        
        for x, y in coords_history[1:]:
            smoothed_x = alpha * smoothed_x + (1 - alpha) * x
            smoothed_y = alpha * smoothed_y + (1 - alpha) * y
        
        return (smoothed_x, smoothed_y)
    
    @staticmethod
    def calculate_fps(frame_times: List[float]) -> float:
        """
        计算帧率
        
        Args:
            frame_times: 帧时间戳列表
        
        Returns:
            帧率值
        """
        if len(frame_times) < 2:
            return 0.0
        
        time_diffs = [frame_times[i] - frame_times[i-1] 
                     for i in range(1, len(frame_times))]
        
        avg_time_diff = sum(time_diffs) / len(time_diffs)
        
        if avg_time_diff == 0:
            return 0.0
        
        return 1.0 / avg_time_diff 