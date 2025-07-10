#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据准备脚本（带数据增强）
运行数据预处理流程，包含多种数据增强技术
"""

import sys
import os
from pathlib import Path
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_processing.preprocessor import DataPreprocessor
from src.utils.config_loader import config_loader


def create_augmentation_config():
    """创建数据增强配置"""
    
    # 垃圾分类优化的数据增强配置
    augmentation_config = {
        'augmentation_factor': 5,  # 每张原图生成5张增强图
        'rotation': {
            'enabled': True,
            'max_angle': 25,  # 适中的旋转角度，避免过度旋转
            'probability': 0.8
        },
        'brightness': {
            'enabled': True,
            'factor_range': (0.7, 1.3),  # 适应不同光照条件
            'probability': 0.7
        },
        'noise': {
            'enabled': True,
            'noise_type': 'gaussian',  # 高斯噪声模拟真实环境
            'noise_factor': 0.08,
            'probability': 0.4
        },
        'translation': {
            'enabled': True,
            'max_shift': 0.15,  # 适中的平移范围
            'probability': 0.6
        },
        'scaling': {
            'enabled': True,
            'scale_range': (0.85, 1.15),  # 适中的缩放范围
            'probability': 0.6
        },
        'horizontal_flip': {
            'enabled': True,
            'probability': 0.5  # 50%概率水平翻转
        },
        'vertical_flip': {
            'enabled': False,  # 垃圾分类通常不需要垂直翻转
            'probability': 0.1
        },
        'color_enhancement': {
            'enabled': True,
            'saturation_range': (0.8, 1.2),
            'hue_shift_range': (-8, 8),
            'probability': 0.5
        },
        'contrast': {
            'enabled': True,
            'factor_range': (0.8, 1.2),
            'probability': 0.5
        },
        'blur': {
            'enabled': True,
            'kernel_size': (3, 5),  # 轻微模糊
            'probability': 0.3
        },
        'sharpen': {
            'enabled': True,
            'strength': 0.3,  # 适中的锐化强度
            'probability': 0.3
        },
        'gamma_correction': {
            'enabled': True,
            'gamma_range': (0.8, 1.2),
            'probability': 0.4
        }
    }
    
    return augmentation_config


def print_augmentation_info(config):
    """打印数据增强配置信息"""
    print("=" * 60)
    print("🎯 数据增强配置")
    print("=" * 60)
    print(f"增强倍数: {config['augmentation_factor']}x")
    print("\n启用的增强技术:")
    
    enabled_techniques = []
    for technique, settings in config.items():
        if isinstance(settings, dict) and settings.get('enabled', False):
            prob = settings.get('probability', 0) * 100
            enabled_techniques.append(f"  ✅ {technique}: {prob:.0f}% 概率")
    
    for technique in enabled_techniques:
        print(technique)
    
    print(f"\n总共启用 {len(enabled_techniques)} 种增强技术")
    print("=" * 60)


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 SmartBin 垃圾分拣系统 - 数据预处理（含数据增强）")
    print("=" * 80)
    
    # 数据目录配置
    data_dir = "data"  # 原始数据目录
    output_dir = "datasets"  # 输出目录
    
    print(f"📁 数据源目录: {data_dir}")
    print(f"📁 输出目录: {output_dir}")
    
    # 创建数据增强配置
    augmentation_config = create_augmentation_config()
    
    # 显示增强配置
    print_augmentation_info(augmentation_config)
    
    # 保存配置文件
    config_file = Path(output_dir) / "augmentation_config.json"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(augmentation_config, f, indent=2, ensure_ascii=False)
    print(f"💾 增强配置已保存: {config_file}")
    
    # 创建数据预处理器（启用数据增强）
    preprocessor = DataPreprocessor(
        enable_augmentation=True,
        augmentation_config=augmentation_config
    )
    
    # 执行数据预处理
    try:
        print("\n🔄 开始数据预处理...")
        
        # 执行完整的数据处理流程
        final_dataset_dir = preprocessor.process_data(data_dir, output_dir)
        
        # 分析最终数据集
        print("\n📊 分析最终数据集...")
        analysis = preprocessor.analyze_dataset(final_dataset_dir)
        
        # 显示统计信息
        print("\n" + "=" * 50)
        print("📈 数据集统计信息")
        print("=" * 50)
        
        print(f"总图像数: {analysis['total_images']}")
        print(f"总对象数: {analysis['total_objects']}")
        
        print("\n数据集划分:")
        for split, info in analysis['splits'].items():
            percentage = (info['image_count'] / analysis['total_images']) * 100 if analysis['total_images'] > 0 else 0
            print(f"  {split:>5}: {info['image_count']:>5} 张图像 ({percentage:.1f}%), {info['object_count']:>5} 个对象")
        
        print("\n类别分布:")
        for class_name, count in analysis['class_distribution'].items():
            print(f"  {class_name:>15}: {count:>5} 个标注")
        
        print(f"\n📍 最终数据集位置: {final_dataset_dir}")
        print(f"📍 配置文件位置: {Path(final_dataset_dir) / 'dataset.yaml'}")
        
        # 计算增强效果
        original_estimate = analysis['total_images'] // (augmentation_config['augmentation_factor'] + 1)
        augmented_estimate = analysis['total_images'] - original_estimate
        
        print(f"\n🎯 数据增强效果估算:")
        print(f"  原始图像: ~{original_estimate} 张")
        print(f"  增强图像: ~{augmented_estimate} 张")
        print(f"  增强倍数: {analysis['total_images']/original_estimate:.1f}x" if original_estimate > 0 else "  增强倍数: 计算中...")
        
        print("\n" + "=" * 80)
        print("🎉 数据预处理完成！模型训练数据已准备就绪")
        print("=" * 80)
        
        # 提供后续步骤建议
        print("\n🔥 后续步骤建议:")
        print("1. 检查生成的数据集质量")
        print("2. 运行模型训练脚本")
        print("3. 调整增强参数（如需要）")
        print("4. 根据训练结果优化配置")
        
    except Exception as e:
        print(f"❌ 数据预处理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def create_light_augmentation_config():
    """创建轻量级数据增强配置（适合测试）"""
    return {
        'augmentation_factor': 2,
        'rotation': {'enabled': True, 'max_angle': 15, 'probability': 0.5},
        'brightness': {'enabled': True, 'factor_range': (0.8, 1.2), 'probability': 0.5},
        'horizontal_flip': {'enabled': True, 'probability': 0.5},
        'noise': {'enabled': False},
        'translation': {'enabled': False},
        'scaling': {'enabled': False},
        'vertical_flip': {'enabled': False},
        'color_enhancement': {'enabled': False},
        'contrast': {'enabled': False},
        'blur': {'enabled': False},
        'sharpen': {'enabled': False},
        'gamma_correction': {'enabled': False}
    }


def create_heavy_augmentation_config():
    """创建重度数据增强配置（适合数据稀少的情况）"""
    return {
        'augmentation_factor': 8,
        'rotation': {'enabled': True, 'max_angle': 35, 'probability': 0.9},
        'brightness': {'enabled': True, 'factor_range': (0.6, 1.4), 'probability': 0.8},
        'noise': {'enabled': True, 'noise_type': 'gaussian', 'noise_factor': 0.12, 'probability': 0.6},
        'translation': {'enabled': True, 'max_shift': 0.2, 'probability': 0.7},
        'scaling': {'enabled': True, 'scale_range': (0.8, 1.2), 'probability': 0.7},
        'horizontal_flip': {'enabled': True, 'probability': 0.5},
        'vertical_flip': {'enabled': True, 'probability': 0.3},
        'color_enhancement': {'enabled': True, 'saturation_range': (0.7, 1.3), 'hue_shift_range': (-15, 15), 'probability': 0.6},
        'contrast': {'enabled': True, 'factor_range': (0.7, 1.3), 'probability': 0.6},
        'blur': {'enabled': True, 'kernel_size': (3, 7), 'probability': 0.4},
        'sharpen': {'enabled': True, 'strength': 0.5, 'probability': 0.4},
        'gamma_correction': {'enabled': True, 'gamma_range': (0.7, 1.3), 'probability': 0.5}
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据预处理脚本（带数据增强）')
    parser.add_argument('--mode', choices=['normal', 'light', 'heavy'], default='normal',
                        help='增强模式: normal(标准), light(轻量), heavy(重度)')
    parser.add_argument('--no-augmentation', action='store_true',
                        help='禁用数据增强')
    
    args = parser.parse_args()
    
    if args.no_augmentation:
        print("⚠️ 数据增强已禁用")
        # 运行不带增强的预处理
        preprocessor = DataPreprocessor(enable_augmentation=False)
        final_dataset_dir = preprocessor.process_data("data", "datasets")
        print(f"数据集已创建: {final_dataset_dir}")
    else:
        # 根据模式选择配置
        if args.mode == 'light':
            augmentation_config = create_light_augmentation_config()
            print("🔧 使用轻量级数据增强配置")
        elif args.mode == 'heavy':
            augmentation_config = create_heavy_augmentation_config()
            print("🔧 使用重度数据增强配置")
        else:
            augmentation_config = create_augmentation_config()
            print("🔧 使用标准数据增强配置")
        
        # 更新全局配置
        create_augmentation_config = lambda: augmentation_config
        main() 