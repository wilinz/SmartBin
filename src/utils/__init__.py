#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块包
"""

from .config_loader import ConfigLoader

# 延迟导入，避免在不需要时导入OpenCV相关模块
__all__ = ["ConfigLoader", "ImageProcessor", "MathUtils"]

def __getattr__(name):
    if name == "ImageProcessor":
        from .image_utils import ImageProcessor
        return ImageProcessor
    elif name == "MathUtils":
        from .math_utils import MathUtils
        return MathUtils
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 