#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MPS优化版模型训练脚本
专为Apple Silicon GPU优化的YOLOv8垃圾分拣模型训练
"""

import sys
import os
import argparse
from pathlib import Path
import torch

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.trainer import ModelTrainer
from src.utils.config_loader import config_loader


def setup_mps_optimization():
    """设置MPS优化环境"""
    print("🚀 设置Apple Silicon GPU (MPS) 优化...")
    
    # 检查MPS可用性
    if not hasattr(torch.backends, 'mps') or not torch.backends.mps.is_available():
        print("❌ MPS设备不可用，请确保您使用的是搭载Apple Silicon芯片的Mac")
        sys.exit(1)
    
    # MPS优化环境变量
    optimizations = {
        'PYTORCH_MPS_HIGH_WATERMARK_RATIO': '0.0',  # 内存优化
        'PYTORCH_ENABLE_MPS_FALLBACK': '1',         # 启用回退机制
        'MPS_CAPTURE_DEVICE_METRICS': '1',          # 启用性能监控
    }
    
    for key, value in optimizations.items():
        os.environ[key] = value
        print(f"  ✓ {key} = {value}")
    
    # 检测Apple Silicon类型
    try:
        import platform
        chip_info = platform.processor()
        print(f"  ✓ 检测到芯片: {chip_info}")
    except:
        pass
    
    print("✅ MPS优化环境设置完成")


def get_optimal_batch_size(model_size='n'):
    """根据模型大小推荐最佳批处理大小"""
    batch_sizes = {
        'n': 32,   # YOLOv8n - 轻量级
        's': 24,   # YOLOv8s - 小型
        'm': 16,   # YOLOv8m - 中型
        'l': 12,   # YOLOv8l - 大型
        'x': 8     # YOLOv8x - 超大型
    }
    return batch_sizes.get(model_size, 16)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MPS优化版YOLOv8垃圾分拣模型训练')
    parser.add_argument('--data', type=str, default='datasets/yolo_dataset/dataset.yaml', 
                       help='数据集配置文件路径')
    parser.add_argument('--model', type=str, default='yolov8n',
                       help='模型名称 (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)')
    parser.add_argument('--epochs', type=int, default=50,
                       help='训练轮数 (推荐: 50-100)')
    parser.add_argument('--batch', type=int, default=None,
                       help='批次大小 (自动优化)')
    parser.add_argument('--auto-batch', action='store_true', default=True,
                       help='自动优化批处理大小')
    parser.add_argument('--lr', type=float, default=0.01,
                       help='学习率')
    parser.add_argument('--patience', type=int, default=20,
                       help='早停耐心值')
    
    args = parser.parse_args()
    
    print("🍎" * 20)
    print("SmartBin 垃圾分拣系统 - MPS加速训练")
    print("🍎" * 20)
    
    # 设置MPS优化
    setup_mps_optimization()
    
    # 检查数据集文件
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"❌ 错误: 数据集配置文件不存在: {data_path}")
        print("请先运行数据预处理: python scripts/prepare_data.py")
        sys.exit(1)
    
    # 自动优化批处理大小
    if args.auto_batch and args.batch is None:
        model_size = args.model[-1] if args.model.startswith('yolov8') else 'n'
        args.batch = get_optimal_batch_size(model_size)
        print(f"🔧 自动优化批处理大小: {args.batch} (针对 {args.model})")
    
    # 显示训练配置
    print(f"\n📋 训练配置:")
    print(f"  📁 数据集: {data_path}")
    print(f"  🤖 模型: {args.model}")
    print(f"  📦 批次大小: {args.batch}")
    print(f"  🔄 训练轮数: {args.epochs}")
    print(f"  📚 学习率: {args.lr}")
    print(f"  ⏳ 早停耐心: {args.patience}")
    
    try:
        # 创建训练器
        print(f"\n🏗️  初始化训练器...")
        trainer = ModelTrainer()
        
        # 验证MPS设备
        if trainer.device != 'mps':
            print(f"⚠️  警告: 预期使用MPS但检测到设备: {trainer.device}")
        else:
            print(f"✅ MPS设备确认: {trainer.device}")
        
        # 加载模型
        print(f"📥 加载模型: {args.model}")
        trainer.load_model(model_name=args.model, pretrained=True)
        
        # 开始训练
        print(f"\n🚀 开始MPS加速训练...")
        print(f"{'='*50}")
        
        results = trainer.train(
            data_config=str(data_path),
            epochs=args.epochs,
            batch_size=args.batch,
            learning_rate=args.lr,
            patience=args.patience,
            resume=False,
            # MPS特定优化参数
            amp=True,        # 自动混合精度
            cache=True,      # 数据缓存
            workers=0,       # MPS单线程工作
            verbose=True,    # 详细输出
            plots=True,      # 生成训练图表
            save=True,       # 保存检查点
        )
        
        print(f"{'='*50}")
        print(f"🎉 MPS加速训练完成!")
        print(f"{'='*50}")
        print(f"🏆 最佳模型: {results['best_model_path']}")
        print(f"📊 最新模型: {results['last_model_path']}")
        print(f"📁 结果目录: {results['results_dir']}")
        
        # 显示训练图表位置
        results_dir = Path(results['results_dir'])
        if (results_dir / 'results.png').exists():
            print(f"📈 训练图表: {results_dir / 'results.png'}")
        if (results_dir / 'confusion_matrix.png').exists():
            print(f"🔢 混淆矩阵: {results_dir / 'confusion_matrix.png'}")
        
        print(f"\n💡 提示:")
        print(f"  • 可以使用Finder打开结果目录查看训练图表")
        print(f"  • 最佳模型已保存，可用于部署和推理")
        print(f"  • 建议使用验证脚本评估模型性能")
        
        print(f"\n🍎 Apple Silicon GPU加速训练完成!")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  训练被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 