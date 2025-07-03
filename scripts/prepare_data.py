#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据准备脚本
运行数据预处理流程
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_processing.preprocessor import DataPreprocessor
from src.utils.config_loader import config_loader


def main():
    """主函数"""
    print("=" * 60)
    print("SmartBin 垃圾分拣系统 - 数据预处理")
    print("=" * 60)
    
    # 数据目录配置
    data_dir = "data"  # 原始数据目录
    output_dir = "datasets"  # 输出目录
    
    print(f"数据源目录: {data_dir}")
    print(f"输出目录: {output_dir}")
    
    # 创建数据预处理器
    preprocessor = DataPreprocessor()
    
    # 执行数据预处理
    try:
        print("\n开始数据预处理...")
        
        # 执行完整的数据处理流程
        final_dataset_dir = preprocessor.process_data(data_dir, output_dir)
        
        # 分析最终数据集
        print("\n分析最终数据集...")
        analysis = preprocessor.analyze_dataset(final_dataset_dir)
        
        # 显示统计信息
        print("\n" + "=" * 40)
        print("数据集统计信息")
        print("=" * 40)
        
        print(f"总图像数: {analysis['total_images']}")
        print(f"总对象数: {analysis['total_objects']}")
        
        print("\n数据集划分:")
        for split, info in analysis['splits'].items():
            percentage = (info['image_count'] / analysis['total_images']) * 100 if analysis['total_images'] > 0 else 0
            print(f"  {split:>5}: {info['image_count']:>4} 张图像 ({percentage:.1f}%), {info['object_count']:>4} 个对象")
        
        print("\n类别分布:")
        for class_name, count in analysis['class_distribution'].items():
            print(f"  {class_name:>15}: {count:>4} 个标注")
        
        print(f"\n最终数据集位置: {final_dataset_dir}")
        
        print("\n" + "=" * 60)
        print("数据预处理完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"数据预处理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 