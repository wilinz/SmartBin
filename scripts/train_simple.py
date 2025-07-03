#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版模型训练脚本
专注于训练，不进行验证和导出
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.trainer import ModelTrainer
from src.utils.config_loader import config_loader


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='训练YOLOv8垃圾分拣模型（简化版）')
    parser.add_argument('--data', type=str, default='datasets/yolo_dataset/dataset.yaml', 
                       help='数据集配置文件路径')
    parser.add_argument('--model', type=str, default=None,
                       help='模型名称 (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)')
    parser.add_argument('--epochs', type=int, default=10,
                       help='训练轮数')
    parser.add_argument('--batch', type=int, default=None,
                       help='批次大小')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SmartBin 垃圾分拣系统 - 简化训练")
    print("=" * 60)
    
    # 检查数据集文件
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"错误: 数据集配置文件不存在: {data_path}")
        print("请先运行数据预处理: python scripts/prepare_data.py")
        sys.exit(1)
    
    print(f"数据集配置: {data_path}")
    print(f"模型: {args.model or config_loader.get_model_name()}")
    print(f"训练轮数: {args.epochs}")
    
    try:
        # 创建训练器
        trainer = ModelTrainer()
        
        # 加载模型
        trainer.load_model(model_name=args.model, pretrained=True)
        
        # 开始训练
        print("\n开始训练...")
        results = trainer.train(
            data_config=str(data_path),
            epochs=args.epochs,
            batch_size=args.batch,
            resume=False
        )
        
        print("\n" + "=" * 40)
        print("训练完成!")
        print("=" * 40)
        print(f"最佳模型: {results['best_model_path']}")
        print(f"最新模型: {results['last_model_path']}")
        print(f"结果目录: {results['results_dir']}")
        
        print("\n" + "=" * 60)
        print("简化训练流程完成!")
        print("=" * 60)
        print("\n提示:")
        print("- 如需验证模型，请单独运行验证脚本")
        print("- 如需导出模型，请单独运行导出脚本")
        print("- 训练日志和图表保存在结果目录中")
        
    except KeyboardInterrupt:
        print("\n训练被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"训练失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 