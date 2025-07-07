#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型训练模块
基于YOLOv8的垃圾分类模型训练
"""

import os
import sys
from pathlib import Path
import yaml
import time
import logging
from typing import Dict, Any, Optional, List

from ultralytics import YOLO
import torch

from ..utils.config_loader import config_loader


class ModelTrainer:
    """YOLOv8模型训练器"""
    
    def __init__(self):
        self.config = config_loader.get_model_config()
        self.system_config = config_loader.get_system_config()
        self.model = None
        self.training_results = {}
        
        # 设置日志
        self._setup_logging()
        
        # 设置设备
        self.device = self._get_device()
        self.logger.info(f"使用设备: {self.device}")
    
    def _setup_logging(self):
        """设置日志"""
        log_dir = Path(self.system_config.get('paths', {}).get('logs_dir', 'logs'))
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'training.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _get_device(self):
        """获取训练设备（优化版）"""
        import os
        # 优先检查MPS（Apple Silicon GPU）
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            # 设置MPS优化
            if hasattr(torch.backends.mps, 'is_built'):
                self.logger.info(f"检测到Apple Silicon GPU，启用MPS加速")
                # 设置MPS内存优化
                os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
                return 'mps'
        elif torch.cuda.is_available():
            return 'cuda'
        else:
            return 'cpu'
    
    def load_model(self, model_name: Optional[str] = None, pretrained: bool = True):
        """
        加载YOLOv8模型
        
        Args:
            model_name: 模型名称 (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)
            pretrained: 是否使用预训练权重
        """
        if model_name is None:
            model_name = self.config.get('model', {}).get('name', 'yolov8n')
        
        if pretrained:
            model_path = f"{model_name}.pt"
        else:
            model_path = f"{model_name}.yaml"
        
        try:
            # 临时设置环境变量以处理PyTorch 2.6的安全加载问题
            import os
            original_weights_only = os.environ.get('TORCH_WEIGHTS_ONLY', None)
            os.environ['TORCH_WEIGHTS_ONLY'] = 'False'
            
            try:
                self.model = YOLO(model_path)
                self.logger.info(f"成功加载模型: {model_name}")
            finally:
                # 恢复原来的环境变量设置
                if original_weights_only is None:
                    os.environ.pop('TORCH_WEIGHTS_ONLY', None)
                else:
                    os.environ['TORCH_WEIGHTS_ONLY'] = original_weights_only
                    
        except Exception as e:
            self.logger.error(f"加载模型失败: {e}")
            # 如果环境变量方法失败，尝试直接禁用权重安全检查
            try:
                import torch
                # 临时修改torch.load的默认行为
                original_load = torch.load
                
                def safe_load(*args, **kwargs):
                    kwargs.setdefault('weights_only', False)
                    return original_load(*args, **kwargs)
                
                torch.load = safe_load
                try:
                    self.model = YOLO(model_path)
                    self.logger.info(f"使用兼容模式成功加载模型: {model_name}")
                finally:
                    torch.load = original_load
                    
            except Exception as e2:
                self.logger.error(f"兼容模式加载也失败: {e2}")
                raise e
    
    def train(self, 
              data_config: str,
              epochs: Optional[int] = None,
              batch_size: Optional[int] = None,
              learning_rate: Optional[float] = None,
              resume: bool = False,
              **kwargs) -> Dict[str, Any]:
        """
        训练模型
        
        Args:
            data_config: 数据集配置文件路径
            epochs: 训练轮数
            batch_size: 批次大小
            learning_rate: 学习率
            resume: 是否从上次中断处继续训练
            **kwargs: 其他训练参数
        
        Returns:
            训练结果字典
        """
        if self.model is None:
            self.load_model()
        
        # 获取训练参数
        train_config = self.config.get('training', {})
        
        # MPS优化的批处理大小
        default_batch_size = 16
        if self.device == 'mps':
            # 针对MPS优化批处理大小
            default_batch_size = 32  # Apple Silicon通常可以处理更大的批次
            self.logger.info("使用MPS优化的训练参数")
        
        training_args = {
            'data': data_config,
            'epochs': epochs or train_config.get('epochs', 100),
            'batch': batch_size or train_config.get('batch_size', default_batch_size),
            'lr0': learning_rate or train_config.get('learning_rate', 0.01),
            'optimizer': train_config.get('optimizer', 'AdamW'),
            'weight_decay': train_config.get('weight_decay', 0.0005),
            'momentum': train_config.get('momentum', 0.937),
            'warmup_epochs': train_config.get('warmup_epochs', 3),
            'warmup_momentum': train_config.get('warmup_momentum', 0.8),
            'warmup_bias_lr': train_config.get('warmup_bias_lr', 0.1),
            'device': self.device,
            'project': self.system_config.get('paths', {}).get('models_dir', 'models'),
            'name': f'garbage_sorting_{int(time.time())}',
            'save_period': train_config.get('save_period', 10),
            'patience': train_config.get('patience', 50),
            'resume': resume
        }
        
        # MPS特定优化
        if self.device == 'mps':
            # 对于MPS，禁用某些可能导致性能问题的功能
            training_args.update({
                'workers': 0,  # MPS在多进程方面有限制
                'amp': True,   # 启用自动混合精度
                'cache': True, # 启用缓存以减少I/O
            })
            self.logger.info("应用MPS设备特定优化设置")
        
        # 添加数据增强参数
        augmentation = train_config.get('augmentation', {})
        for key, value in augmentation.items():
            training_args[key] = value
        
        # 更新其他参数
        training_args.update(kwargs)
        
        self.logger.info(f"开始训练模型，参数: {training_args}")
        
        try:
            # 开始训练
            results = self.model.train(**training_args)
            
            # 保存训练结果
            self.training_results = {
                'best_model_path': results.save_dir / 'weights' / 'best.pt',
                'last_model_path': results.save_dir / 'weights' / 'last.pt',
                'results_dir': results.save_dir,
                'metrics': results.results_dict if hasattr(results, 'results_dict') else {}
            }
            
            self.logger.info(f"训练完成，模型保存在: {self.training_results['best_model_path']}")
            
            return self.training_results
            
        except Exception as e:
            self.logger.error(f"训练失败: {e}")
            raise
    
    def validate(self, data_config: str, model_path: Optional[str] = None) -> Dict[str, Any]:
        """
        验证模型
        
        Args:
            data_config: 数据集配置文件路径
            model_path: 模型权重文件路径
        
        Returns:
            验证结果字典
        """
        if model_path:
            # 使用相同的兼容性修复来加载模型
            import os
            import torch
            original_weights_only = os.environ.get('TORCH_WEIGHTS_ONLY', None)
            os.environ['TORCH_WEIGHTS_ONLY'] = 'False'
            
            try:
                model = YOLO(model_path)
            except Exception:
                # 备用方法
                original_load = torch.load
                def safe_load(*args, **kwargs):
                    kwargs.setdefault('weights_only', False)
                    return original_load(*args, **kwargs)
                torch.load = safe_load
                try:
                    model = YOLO(model_path)
                finally:
                    torch.load = original_load
            finally:
                if original_weights_only is None:
                    os.environ.pop('TORCH_WEIGHTS_ONLY', None)
                else:
                    os.environ['TORCH_WEIGHTS_ONLY'] = original_weights_only
        else:
            model = self.model
        
        if model is None:
            raise ValueError("模型未加载，请先加载模型或提供模型路径")
        
        self.logger.info("开始模型验证...")
        
        try:
            results = model.val(data=data_config, device=self.device)
            
            val_results = {
                'map50': results.box.map50,
                'map': results.box.map,
                'precision': results.box.mp,
                'recall': results.box.mr,
                'fitness': results.fitness
            }
            
            self.logger.info(f"验证完成，mAP@0.5: {val_results['map50']:.4f}, mAP@0.5:0.95: {val_results['map']:.4f}")
            
            return val_results
            
        except Exception as e:
            self.logger.error(f"验证失败: {e}")
            raise
    
    def export_model(self, 
                    model_path: str,
                    export_format: List[str] = None,
                    **kwargs) -> Dict[str, str]:
        """
        导出模型为不同格式
        
        Args:
            model_path: 模型权重文件路径
            export_format: 导出格式列表 ['onnx', 'engine', 'tflite', 'pb']
            **kwargs: 导出参数
        
        Returns:
            导出文件路径字典
        """
        if export_format is None:
            export_format = self.config.get('export', {}).get('format', ['onnx'])
        
        # 使用兼容性修复来加载模型
        import os
        import torch
        original_weights_only = os.environ.get('TORCH_WEIGHTS_ONLY', None)
        os.environ['TORCH_WEIGHTS_ONLY'] = 'False'
        
        try:
            model = YOLO(model_path)
        except Exception:
            # 备用方法
            original_load = torch.load
            def safe_load(*args, **kwargs):
                kwargs.setdefault('weights_only', False)
                return original_load(*args, **kwargs)
            torch.load = safe_load
            try:
                model = YOLO(model_path)
            finally:
                torch.load = original_load
        finally:
            if original_weights_only is None:
                os.environ.pop('TORCH_WEIGHTS_ONLY', None)
            else:
                os.environ['TORCH_WEIGHTS_ONLY'] = original_weights_only
        export_results = {}
        
        export_config = self.config.get('export', {})
        export_args = {
            'half': export_config.get('half', True),
            'dynamic': export_config.get('dynamic', False),
            'simplify': export_config.get('simplify', True),
            'opset': export_config.get('opset', 11)
        }
        export_args.update(kwargs)
        
        for fmt in export_format:
            try:
                self.logger.info(f"导出模型格式: {fmt}")
                
                if fmt == 'onnx':
                    exported_path = model.export(format='onnx', **export_args)
                elif fmt == 'engine':
                    exported_path = model.export(format='engine', **export_args)
                elif fmt == 'tflite':
                    exported_path = model.export(format='tflite', **export_args)
                elif fmt == 'pb':
                    exported_path = model.export(format='pb', **export_args)
                else:
                    self.logger.warning(f"不支持的导出格式: {fmt}")
                    continue
                
                export_results[fmt] = str(exported_path)
                self.logger.info(f"{fmt.upper()} 模型导出完成: {exported_path}")
                
            except Exception as e:
                self.logger.error(f"导出 {fmt} 格式失败: {e}")
        
        return export_results
    
    def get_training_progress(self) -> Dict[str, Any]:
        """获取训练进度信息"""
        if not self.training_results:
            return {"status": "未开始训练"}
        
        return {
            "status": "训练完成",
            "results": self.training_results
        }
    
    def save_training_config(self, config_path: str):
        """保存训练配置"""
        config_data = {
            'model_config': self.config,
            'training_results': self.training_results,
            'device': self.device,
            'timestamp': time.time()
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
        self.logger.info(f"训练配置已保存到: {config_path}")


def create_trainer() -> ModelTrainer:
    """创建模型训练器实例"""
    return ModelTrainer() 