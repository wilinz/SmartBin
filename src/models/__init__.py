#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型模块
包含垃圾检测器和模型训练器
"""

# 使用延迟导入策略，避免在导入时就加载OpenCV相关模块
__all__ = ["GarbageDetector", "ModelTrainer"]

def __getattr__(name):
    if name == "GarbageDetector":
        try:
            from .detector import GarbageDetector
            return GarbageDetector
        except ImportError as e:
            raise AttributeError(f"module '{__name__}' has no attribute '{name}' (导入失败: {e})")
    elif name == "ModelTrainer":
        try:
            from .trainer import ModelTrainer
            return ModelTrainer
        except ImportError as e:
            raise AttributeError(f"module '{__name__}' has no attribute '{name}' (导入失败: {e})")
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 