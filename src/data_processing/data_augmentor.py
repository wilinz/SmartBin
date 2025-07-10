#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据增强模块
实现各种图像增强技术，同时处理对应的标注框变换
"""

import cv2
import numpy as np
import random
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import json
import math


class DataAugmentor:
    """数据增强器
    
    支持的增强技术:
    1. 旋转 (rotation)
    2. 亮度调节 (brightness)
    3. 噪音添加 (noise)
    4. 平移 (translation)
    5. 缩放 (scaling)
    6. 水平翻转 (horizontal_flip)
    7. 垂直翻转 (vertical_flip)
    8. 颜色增强 (color_enhancement)
    9. 对比度调节 (contrast)
    10. 模糊 (blur)
    11. 锐化 (sharpen)
    12. 伽马校正 (gamma_correction)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化数据增强器
        
        Args:
            config: 增强配置字典
        """
        # 默认配置
        self.default_config = {
            'augmentation_factor': 5,  # 每张原图生成5张增强图
            'rotation': {
                'enabled': True,
                'max_angle': 30,  # 最大旋转角度
                'probability': 0.7
            },
            'brightness': {
                'enabled': True,
                'factor_range': (0.6, 1.4),  # 亮度调节范围
                'probability': 0.6
            },
            'noise': {
                'enabled': True,
                'noise_type': 'gaussian',  # 'gaussian', 'uniform', 'salt_pepper'
                'noise_factor': 0.1,
                'probability': 0.4
            },
            'translation': {
                'enabled': True,
                'max_shift': 0.1,  # 相对于图像尺寸的最大平移比例
                'probability': 0.5
            },
            'scaling': {
                'enabled': True,
                'scale_range': (0.8, 1.2),  # 缩放范围
                'probability': 0.5
            },
            'horizontal_flip': {
                'enabled': True,
                'probability': 0.5
            },
            'vertical_flip': {
                'enabled': False,  # 垃圾分类通常不需要垂直翻转
                'probability': 0.2
            },
            'color_enhancement': {
                'enabled': True,
                'saturation_range': (0.7, 1.3),
                'hue_shift_range': (-10, 10),
                'probability': 0.5
            },
            'contrast': {
                'enabled': True,
                'factor_range': (0.7, 1.3),
                'probability': 0.5
            },
            'blur': {
                'enabled': True,
                'kernel_size': (3, 7),  # 模糊核大小范围
                'probability': 0.3
            },
            'sharpen': {
                'enabled': True,
                'strength': 0.5,
                'probability': 0.3
            },
            'gamma_correction': {
                'enabled': True,
                'gamma_range': (0.7, 1.3),
                'probability': 0.4
            }
        }
        
        # 合并用户配置
        self.config = self.default_config.copy()
        if config:
            self._merge_config(self.config, config)
    
    def _merge_config(self, base_config: Dict, user_config: Dict):
        """递归合并配置"""
        for key, value in user_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._merge_config(base_config[key], value)
            else:
                base_config[key] = value
    
    def augment_image_with_annotations(self, image: np.ndarray, annotations: List[Dict]) -> List[Tuple[np.ndarray, List[Dict]]]:
        """对图像和标注进行增强
        
        Args:
            image: 输入图像 (H, W, C)
            annotations: 标注列表，每个元素包含YOLO格式的坐标
            
        Returns:
            增强后的图像和标注对列表
        """
        augmented_pairs = []
        
        # 原图也要包含在内
        augmented_pairs.append((image.copy(), annotations.copy()))
        
        # 生成增强数据
        for i in range(self.config['augmentation_factor']):
            aug_image = image.copy()
            aug_annotations = [ann.copy() for ann in annotations]
            
            # 随机选择要应用的增强技术
            applied_augmentations = []
            
            # 1. 旋转
            if self._should_apply('rotation'):
                angle = random.uniform(-self.config['rotation']['max_angle'], 
                                     self.config['rotation']['max_angle'])
                aug_image, aug_annotations = self._apply_rotation(aug_image, aug_annotations, angle)
                applied_augmentations.append(f"rotation_{angle:.1f}")
            
            # 2. 缩放
            if self._should_apply('scaling'):
                scale = random.uniform(*self.config['scaling']['scale_range'])
                aug_image, aug_annotations = self._apply_scaling(aug_image, aug_annotations, scale)
                applied_augmentations.append(f"scale_{scale:.2f}")
            
            # 3. 平移
            if self._should_apply('translation'):
                dx = random.uniform(-self.config['translation']['max_shift'], 
                                  self.config['translation']['max_shift'])
                dy = random.uniform(-self.config['translation']['max_shift'], 
                                  self.config['translation']['max_shift'])
                aug_image, aug_annotations = self._apply_translation(aug_image, aug_annotations, dx, dy)
                applied_augmentations.append(f"translate_{dx:.2f}_{dy:.2f}")
            
            # 4. 水平翻转
            if self._should_apply('horizontal_flip'):
                aug_image, aug_annotations = self._apply_horizontal_flip(aug_image, aug_annotations)
                applied_augmentations.append("hflip")
            
            # 5. 垂直翻转
            if self._should_apply('vertical_flip'):
                aug_image, aug_annotations = self._apply_vertical_flip(aug_image, aug_annotations)
                applied_augmentations.append("vflip")
            
            # 6. 亮度调节
            if self._should_apply('brightness'):
                factor = random.uniform(*self.config['brightness']['factor_range'])
                aug_image = self._apply_brightness(aug_image, factor)
                applied_augmentations.append(f"brightness_{factor:.2f}")
            
            # 7. 对比度调节
            if self._should_apply('contrast'):
                factor = random.uniform(*self.config['contrast']['factor_range'])
                aug_image = self._apply_contrast(aug_image, factor)
                applied_augmentations.append(f"contrast_{factor:.2f}")
            
            # 8. 颜色增强
            if self._should_apply('color_enhancement'):
                aug_image = self._apply_color_enhancement(aug_image)
                applied_augmentations.append("color_enh")
            
            # 9. 噪音添加
            if self._should_apply('noise'):
                aug_image = self._apply_noise(aug_image)
                applied_augmentations.append("noise")
            
            # 10. 模糊
            if self._should_apply('blur'):
                kernel_size = random.randint(*self.config['blur']['kernel_size'])
                if kernel_size % 2 == 0:
                    kernel_size += 1
                aug_image = self._apply_blur(aug_image, kernel_size)
                applied_augmentations.append(f"blur_{kernel_size}")
            
            # 11. 锐化
            if self._should_apply('sharpen'):
                aug_image = self._apply_sharpen(aug_image)
                applied_augmentations.append("sharpen")
            
            # 12. 伽马校正
            if self._should_apply('gamma_correction'):
                gamma = random.uniform(*self.config['gamma_correction']['gamma_range'])
                aug_image = self._apply_gamma_correction(aug_image, gamma)
                applied_augmentations.append(f"gamma_{gamma:.2f}")
            
            # 过滤掉无效的标注框
            aug_annotations = self._filter_valid_annotations(aug_annotations)
            
            # 只有当还有有效标注时才添加
            if aug_annotations:
                augmented_pairs.append((aug_image, aug_annotations))
        
        return augmented_pairs
    
    def _should_apply(self, augmentation_type: str) -> bool:
        """判断是否应该应用某种增强技术"""
        config = self.config.get(augmentation_type, {})
        return config.get('enabled', False) and random.random() < config.get('probability', 0.5)
    
    def _apply_rotation(self, image: np.ndarray, annotations: List[Dict], angle: float) -> Tuple[np.ndarray, List[Dict]]:
        """应用旋转变换"""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        # 计算旋转矩阵
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 旋转图像
        rotated_image = cv2.warpAffine(image, rotation_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
        
        # 旋转标注框
        rotated_annotations = []
        for ann in annotations:
            # YOLO格式转换为绝对坐标
            x_center = ann['x_center'] * w
            y_center = ann['y_center'] * h
            width = ann['width'] * w
            height = ann['height'] * h
            
            # 计算四个角点
            corners = np.array([
                [x_center - width/2, y_center - height/2],
                [x_center + width/2, y_center - height/2],
                [x_center + width/2, y_center + height/2],
                [x_center - width/2, y_center + height/2]
            ])
            
            # 应用旋转
            ones = np.ones(shape=(corners.shape[0], 1))
            corners_homogeneous = np.hstack([corners, ones])
            rotated_corners = rotation_matrix.dot(corners_homogeneous.T).T
            
            # 计算新的边界框
            x_min, y_min = np.min(rotated_corners, axis=0)
            x_max, y_max = np.max(rotated_corners, axis=0)
            
            # 裁剪到图像边界
            x_min = max(0, x_min)
            y_min = max(0, y_min)
            x_max = min(w, x_max)
            y_max = min(h, y_max)
            
            # 检查边界框是否仍然有效
            if x_max > x_min and y_max > y_min:
                new_x_center = (x_min + x_max) / 2 / w
                new_y_center = (y_min + y_max) / 2 / h
                new_width = (x_max - x_min) / w
                new_height = (y_max - y_min) / h
                
                rotated_annotations.append({
                    'class_id': ann['class_id'],
                    'class_name': ann['class_name'],
                    'x_center': new_x_center,
                    'y_center': new_y_center,
                    'width': new_width,
                    'height': new_height
                })
        
        return rotated_image, rotated_annotations
    
    def _apply_scaling(self, image: np.ndarray, annotations: List[Dict], scale: float) -> Tuple[np.ndarray, List[Dict]]:
        """应用缩放变换"""
        h, w = image.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        
        # 缩放图像
        scaled_image = cv2.resize(image, (new_w, new_h))
        
        # 如果缩放后尺寸小于原图，需要填充
        if scale < 1.0:
            # 创建原尺寸的图像并将缩放后的图像居中放置
            result_image = np.zeros((h, w, 3), dtype=image.dtype)
            start_x = (w - new_w) // 2
            start_y = (h - new_h) // 2
            result_image[start_y:start_y+new_h, start_x:start_x+new_w] = scaled_image
            
            # 调整标注框坐标
            scaled_annotations = []
            for ann in annotations:
                new_x_center = (ann['x_center'] * scale) + (1 - scale) / 2
                new_y_center = (ann['y_center'] * scale) + (1 - scale) / 2
                new_width = ann['width'] * scale
                new_height = ann['height'] * scale
                
                scaled_annotations.append({
                    'class_id': ann['class_id'],
                    'class_name': ann['class_name'],
                    'x_center': new_x_center,
                    'y_center': new_y_center,
                    'width': new_width,
                    'height': new_height
                })
        else:
            # 缩放后裁剪到原尺寸
            start_x = (new_w - w) // 2
            start_y = (new_h - h) // 2
            result_image = scaled_image[start_y:start_y+h, start_x:start_x+w]
            
            # 调整标注框坐标
            scaled_annotations = []
            for ann in annotations:
                new_x_center = (ann['x_center'] * scale) - (scale - 1) / 2
                new_y_center = (ann['y_center'] * scale) - (scale - 1) / 2
                new_width = ann['width'] * scale
                new_height = ann['height'] * scale
                
                # 检查是否仍在图像范围内
                if (new_x_center - new_width/2 < 1.0 and new_x_center + new_width/2 > 0 and
                    new_y_center - new_height/2 < 1.0 and new_y_center + new_height/2 > 0):
                    
                    scaled_annotations.append({
                        'class_id': ann['class_id'],
                        'class_name': ann['class_name'],
                        'x_center': new_x_center,
                        'y_center': new_y_center,
                        'width': new_width,
                        'height': new_height
                    })
        
        return result_image, scaled_annotations
    
    def _apply_translation(self, image: np.ndarray, annotations: List[Dict], dx: float, dy: float) -> Tuple[np.ndarray, List[Dict]]:
        """应用平移变换"""
        h, w = image.shape[:2]
        
        # 计算平移矩阵
        translation_matrix = np.float32([[1, 0, dx * w], [0, 1, dy * h]])
        
        # 平移图像
        translated_image = cv2.warpAffine(image, translation_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
        
        # 调整标注框坐标
        translated_annotations = []
        for ann in annotations:
            new_x_center = ann['x_center'] + dx
            new_y_center = ann['y_center'] + dy
            
            # 检查是否仍在图像范围内
            if (new_x_center - ann['width']/2 < 1.0 and new_x_center + ann['width']/2 > 0 and
                new_y_center - ann['height']/2 < 1.0 and new_y_center + ann['height']/2 > 0):
                
                translated_annotations.append({
                    'class_id': ann['class_id'],
                    'class_name': ann['class_name'],
                    'x_center': new_x_center,
                    'y_center': new_y_center,
                    'width': ann['width'],
                    'height': ann['height']
                })
        
        return translated_image, translated_annotations
    
    def _apply_horizontal_flip(self, image: np.ndarray, annotations: List[Dict]) -> Tuple[np.ndarray, List[Dict]]:
        """应用水平翻转"""
        flipped_image = cv2.flip(image, 1)
        
        flipped_annotations = []
        for ann in annotations:
            new_x_center = 1.0 - ann['x_center']
            
            flipped_annotations.append({
                'class_id': ann['class_id'],
                'class_name': ann['class_name'],
                'x_center': new_x_center,
                'y_center': ann['y_center'],
                'width': ann['width'],
                'height': ann['height']
            })
        
        return flipped_image, flipped_annotations
    
    def _apply_vertical_flip(self, image: np.ndarray, annotations: List[Dict]) -> Tuple[np.ndarray, List[Dict]]:
        """应用垂直翻转"""
        flipped_image = cv2.flip(image, 0)
        
        flipped_annotations = []
        for ann in annotations:
            new_y_center = 1.0 - ann['y_center']
            
            flipped_annotations.append({
                'class_id': ann['class_id'],
                'class_name': ann['class_name'],
                'x_center': ann['x_center'],
                'y_center': new_y_center,
                'width': ann['width'],
                'height': ann['height']
            })
        
        return flipped_image, flipped_annotations
    
    def _apply_brightness(self, image: np.ndarray, factor: float) -> np.ndarray:
        """应用亮度调节"""
        return np.clip(image * factor, 0, 255).astype(np.uint8)
    
    def _apply_contrast(self, image: np.ndarray, factor: float) -> np.ndarray:
        """应用对比度调节"""
        mean = np.mean(image)
        return np.clip((image - mean) * factor + mean, 0, 255).astype(np.uint8)
    
    def _apply_color_enhancement(self, image: np.ndarray) -> np.ndarray:
        """应用颜色增强"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        
        # 调整饱和度
        saturation_factor = random.uniform(*self.config['color_enhancement']['saturation_range'])
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_factor, 0, 255)
        
        # 调整色调
        hue_shift = random.uniform(*self.config['color_enhancement']['hue_shift_range'])
        hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180
        
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    def _apply_noise(self, image: np.ndarray) -> np.ndarray:
        """应用噪音"""
        noise_type = self.config['noise']['noise_type']
        factor = self.config['noise']['noise_factor']
        
        if noise_type == 'gaussian':
            noise = np.random.normal(0, factor * 255, image.shape).astype(np.float32)
            noisy_image = image.astype(np.float32) + noise
        elif noise_type == 'uniform':
            noise = np.random.uniform(-factor * 255, factor * 255, image.shape).astype(np.float32)
            noisy_image = image.astype(np.float32) + noise
        elif noise_type == 'salt_pepper':
            noisy_image = image.copy().astype(np.float32)
            salt_pepper_mask = np.random.random(image.shape[:2]) < factor
            noisy_image[salt_pepper_mask] = np.random.choice([0, 255], size=np.sum(salt_pepper_mask))
        else:
            return image
        
        return np.clip(noisy_image, 0, 255).astype(np.uint8)
    
    def _apply_blur(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """应用模糊"""
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    
    def _apply_sharpen(self, image: np.ndarray) -> np.ndarray:
        """应用锐化"""
        strength = self.config['sharpen']['strength']
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]) * strength
        kernel[1, 1] = 8 * strength + 1
        return cv2.filter2D(image, -1, kernel)
    
    def _apply_gamma_correction(self, image: np.ndarray, gamma: float) -> np.ndarray:
        """应用伽马校正"""
        look_up_table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype(np.uint8)
        return cv2.LUT(image, look_up_table)
    
    def _filter_valid_annotations(self, annotations: List[Dict]) -> List[Dict]:
        """过滤有效的标注框"""
        valid_annotations = []
        for ann in annotations:
            # 检查边界框是否有效
            if (ann['x_center'] > 0 and ann['x_center'] < 1 and
                ann['y_center'] > 0 and ann['y_center'] < 1 and
                ann['width'] > 0 and ann['width'] < 1 and
                ann['height'] > 0 and ann['height'] < 1):
                valid_annotations.append(ann)
        return valid_annotations
    
    def save_config(self, config_path: str):
        """保存配置到文件"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def load_config(self, config_path: str):
        """从文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            self._merge_config(self.config, config) 