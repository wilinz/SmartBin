#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
垃圾分拣系统 - 源代码包
SmartBin Garbage Sorting System
"""

__version__ = "1.0.0"
__author__ = "SmartBin Team"
__email__ = "team@smartbin.com"
__description__ = "基于YOLOv8的智能垃圾分拣系统"

# 安全导入主要模块
try:
    from .data_processing import DataPreprocessor
except ImportError:
    DataPreprocessor = None

try:
    from .utils import ConfigLoader
except ImportError:
    ConfigLoader = None

# 动态构建 __all__ 列表
__all__ = []
if DataPreprocessor:
    __all__.append("DataPreprocessor")
if ConfigLoader:
    __all__.append("ConfigLoader")

def __getattr__(name):
    if name == "DataPreprocessor" and DataPreprocessor:
        return DataPreprocessor
    elif name == "ConfigLoader" and ConfigLoader:
        return ConfigLoader
    elif name == "GarbageDetector":
        try:
            from .models import GarbageDetector
            return GarbageDetector
        except (ImportError, AttributeError):
            raise AttributeError(f"module '{__name__}' has no attribute '{name}' (未实现)")
    elif name == "ModelTrainer":
        try:
            from .models import ModelTrainer
            return ModelTrainer
        except (ImportError, AttributeError):
            raise AttributeError(f"module '{__name__}' has no attribute '{name}' (未实现)")
    elif name == "SystemController":
        try:
            from .system import SystemController
            return SystemController
        except (ImportError, AttributeError):
            raise AttributeError(f"module '{__name__}' has no attribute '{name}' (未实现)")
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 