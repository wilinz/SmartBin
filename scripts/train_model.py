#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型训练脚本
训练YOLOv8垃圾分拣模型
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
    parser = argparse.ArgumentParser(description='训练YOLOv8垃圾分拣模型')
    parser.add_argument('--data', type=str, default='dataset/dataset.yaml', 
                       help='数据集配置文件路径')
    parser.add_argument('--model', type=str, default=None,
                       help='模型名称 (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)')
    parser.add_argument('--epochs', type=int, default=None,
                       help='训练轮数')
    parser.add_argument('--batch', type=int, default=None,
                       help='批次大小')
    parser.add_argument('--lr', type=float, default=None,
                       help='学习率')
    parser.add_argument('--resume', action='store_true',
                       help='从上次中断处继续训练')
    parser.add_argument('--pretrained', action='store_true', default=True,
                       help='使用预训练权重')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SmartBin 垃圾分拣系统 - 模型训练")
    print("=" * 60)
    
    # 检查数据集文件
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"错误: 数据集配置文件不存在: {data_path}")
        print("请先运行数据预处理: python scripts/prepare_data.py")
        sys.exit(1)
    
    print(f"数据集配置: {data_path}")
    print(f"模型: {args.model or config_loader.get_model_name()}")
    print(f"预训练权重: {'是' if args.pretrained else '否'}")
    
    try:
        # 创建训练器
        trainer = ModelTrainer()
        
        # 加载模型
        trainer.load_model(model_name=args.model, pretrained=args.pretrained)
        
        # 开始训练
        print("\n开始训练...")
        results = trainer.train(
            data_config=str(data_path),
            epochs=args.epochs,
            batch_size=args.batch,
            learning_rate=args.lr,
            resume=args.resume
        )
        
        print("\n" + "=" * 40)
        print("训练完成!")
        print("=" * 40)
        print(f"最佳模型: {results['best_model_path']}")
        print(f"最新模型: {results['last_model_path']}")
        print(f"结果目录: {results['results_dir']}")
        
        # 验证模型
        print("\n开始模型验证...")
        val_results = trainer.validate(str(data_path), str(results['best_model_path']))
        
        print(f"验证结果:")
        print(f"  mAP@0.5: {val_results['map50']:.4f}")
        print(f"  mAP@0.5:0.95: {val_results['map']:.4f}")
        print(f"  精确度: {val_results['precision']:.4f}")
        print(f"  召回率: {val_results['recall']:.4f}")
        
        # 导出模型
        print("\n导出模型...")
        export_results = trainer.export_model(str(results['best_model_path']))
        
        print("导出完成:")
        for fmt, path in export_results.items():
            print(f"  {fmt.upper()}: {path}")
        
        print("\n" + "=" * 60)
        print("模型训练流程完成!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n训练被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"训练失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 