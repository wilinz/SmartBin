#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像处理工具
提供图像处理相关的实用功能
"""

import cv2
import numpy as np
from PIL import Image
import base64
import io
from typing import Tuple, Optional, Union


class ImageProcessor:
    """图像处理工具类"""
    
    @staticmethod
    def resize_image(image: np.ndarray, 
                    size: Tuple[int, int], 
                    keep_aspect_ratio: bool = True) -> np.ndarray:
        """
        调整图像大小
        
        Args:
            image: 输入图像
            size: 目标尺寸 (width, height)
            keep_aspect_ratio: 是否保持宽高比
        
        Returns:
            调整大小后的图像
        """
        if not keep_aspect_ratio:
            return cv2.resize(image, size)
        
        h, w = image.shape[:2]
        target_w, target_h = size
        
        # 计算缩放比例
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        # 调整大小
        resized = cv2.resize(image, (new_w, new_h))
        
        # 添加填充
        delta_w = target_w - new_w
        delta_h = target_h - new_h
        top, bottom = delta_h // 2, delta_h - (delta_h // 2)
        left, right = delta_w // 2, delta_w - (delta_w // 2)
        
        # 使用黑色填充
        padded = cv2.copyMakeBorder(resized, top, bottom, left, right, 
                                   cv2.BORDER_CONSTANT, value=[0, 0, 0])
        
        return padded
    
    @staticmethod
    def normalize_image(image: np.ndarray) -> np.ndarray:
        """
        归一化图像像素值到[0,1]范围
        
        Args:
            image: 输入图像
        
        Returns:
            归一化后的图像
        """
        return image.astype(np.float32) / 255.0
    
    @staticmethod
    def denormalize_image(image: np.ndarray) -> np.ndarray:
        """
        反归一化图像像素值到[0,255]范围
        
        Args:
            image: 归一化的图像
        
        Returns:
            反归一化后的图像
        """
        return (image * 255).astype(np.uint8)
    
    @staticmethod
    def bgr_to_rgb(image: np.ndarray) -> np.ndarray:
        """BGR转RGB"""
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    @staticmethod
    def rgb_to_bgr(image: np.ndarray) -> np.ndarray:
        """RGB转BGR"""
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    
    @staticmethod
    def image_to_base64(image: np.ndarray, format: str = 'JPEG') -> str:
        """
        将图像转换为base64字符串
        
        Args:
            image: 输入图像 (BGR格式)
            format: 图像格式
        
        Returns:
            base64编码的图像字符串
        """
        # 转换为RGB格式
        if len(image.shape) == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        # 转换为PIL Image
        pil_image = Image.fromarray(image_rgb)
        
        # 转换为base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format=format)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/{format.lower()};base64,{img_str}"
    
    @staticmethod
    def base64_to_image(base64_str: str) -> np.ndarray:
        """
        将base64字符串转换为图像
        
        Args:
            base64_str: base64编码的图像字符串
        
        Returns:
            图像数组 (BGR格式)
        """
        # 移除data URL前缀
        if base64_str.startswith('data:image'):
            base64_str = base64_str.split(',')[1]
        
        # 解码base64
        img_data = base64.b64decode(base64_str)
        
        # 转换为numpy数组
        nparr = np.frombuffer(img_data, np.uint8)
        
        # 解码图像
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return image
    
    @staticmethod
    def draw_bounding_boxes(image: np.ndarray, 
                           boxes: list, 
                           labels: list = None,
                           scores: list = None,
                           colors: list = None) -> np.ndarray:
        """
        在图像上绘制边界框
        
        Args:
            image: 输入图像
            boxes: 边界框列表，格式为 [[x1, y1, x2, y2], ...]
            labels: 标签列表
            scores: 置信度分数列表
            colors: 颜色列表
        
        Returns:
            绘制了边界框的图像
        """
        result_image = image.copy()
        
        # 默认颜色
        if colors is None:
            colors = [(0, 255, 0)] * len(boxes)  # 绿色
        
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box)
            color = colors[i % len(colors)]
            
            # 绘制边界框
            cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签和置信度
            if labels is not None:
                label_text = labels[i]
                if scores is not None:
                    label_text += f" {scores[i]:.2f}"
                
                # 计算文本尺寸
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness = 1
                (text_width, text_height), _ = cv2.getTextSize(
                    label_text, font, font_scale, thickness
                )
                
                # 绘制文本背景
                cv2.rectangle(result_image, 
                             (x1, y1 - text_height - 10),
                             (x1 + text_width, y1), 
                             color, -1)
                
                # 绘制文本
                cv2.putText(result_image, label_text,
                           (x1, y1 - 5), font, font_scale,
                           (255, 255, 255), thickness)
        
        return result_image
    
    @staticmethod
    def enhance_image(image: np.ndarray, 
                     brightness: float = 0.0,
                     contrast: float = 1.0,
                     gamma: float = 1.0) -> np.ndarray:
        """
        图像增强
        
        Args:
            image: 输入图像
            brightness: 亮度调整 (-100 到 100)
            contrast: 对比度调整 (0.5 到 2.0)
            gamma: 伽马校正 (0.5 到 2.0)
        
        Returns:
            增强后的图像
        """
        # 亮度调整
        if brightness != 0:
            if brightness > 0:
                shadow = brightness
                highlight = 255
            else:
                shadow = 0
                highlight = 255 + brightness
            alpha_b = (highlight - shadow) / 255
            gamma_b = shadow
            image = cv2.addWeighted(image, alpha_b, image, 0, gamma_b)
        
        # 对比度调整
        if contrast != 1.0:
            image = cv2.convertScaleAbs(image, alpha=contrast, beta=0)
        
        # 伽马校正
        if gamma != 1.0:
            inv_gamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 
                             for i in np.arange(0, 256)]).astype(np.uint8)
            image = cv2.LUT(image, table)
        
        return image
    
    @staticmethod
    def crop_image(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        根据边界框裁剪图像
        
        Args:
            image: 输入图像
            bbox: 边界框 (x1, y1, x2, y2)
        
        Returns:
            裁剪后的图像
        """
        x1, y1, x2, y2 = bbox
        return image[y1:y2, x1:x2]
    
    @staticmethod
    def calculate_image_stats(image: np.ndarray) -> dict:
        """
        计算图像统计信息
        
        Args:
            image: 输入图像
        
        Returns:
            统计信息字典
        """
        stats = {
            'shape': image.shape,
            'dtype': str(image.dtype),
            'min': float(np.min(image)),
            'max': float(np.max(image)),
            'mean': float(np.mean(image)),
            'std': float(np.std(image))
        }
        
        if len(image.shape) == 3:
            stats['channels'] = image.shape[2]
            for i in range(image.shape[2]):
                channel_name = ['Blue', 'Green', 'Red'][i] if image.shape[2] == 3 else f'Channel_{i}'
                stats[f'{channel_name}_mean'] = float(np.mean(image[:, :, i]))
                stats[f'{channel_name}_std'] = float(np.std(image[:, :, i]))
        
        return stats 