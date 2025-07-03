#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理模块
包含数据预处理、数据增强、数据分析等功能
"""

from .preprocessor import DataPreprocessor

# 延迟导入其他模块（如果需要）
__all__ = ["DataPreprocessor"]

def __getattr__(name):
    if name == "DataAugmentation":
        try:
            from .augmentation import DataAugmentation
            return DataAugmentation
        except ImportError:
            raise AttributeError(f"module '{__name__}' has no attribute '{name}' (未实现)")
    elif name == "DataAnalyzer":
        try:
            from .analyzer import DataAnalyzer
            return DataAnalyzer
        except ImportError:
            raise AttributeError(f"module '{__name__}' has no attribute '{name}' (未实现)")
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 