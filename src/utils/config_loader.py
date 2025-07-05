#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
用于加载和管理系统配置文件
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._configs = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """加载所有配置文件"""
        config_files = {
            'model': 'model_config.yaml',
            'system': 'system_config.yaml', 
            'hardware': 'hardware_config.yaml'
        }
        
        for config_name, filename in config_files.items():
            config_path = self.config_dir / filename
            if config_path.exists():
                self._configs[config_name] = self._load_yaml(config_path)
            else:
                print(f"警告: 配置文件 {filename} 不存在")
                self._configs[config_name] = {}
    
    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"加载配置文件 {file_path} 失败: {e}")
            return {}
    
    def get_config(self, config_type: str) -> Dict[str, Any]:
        """获取指定类型的配置"""
        return self._configs.get(config_type, {})
    
    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        return self.get_config('model')
    
    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.get_config('system')
    
    def get_hardware_config(self) -> Dict[str, Any]:
        """获取硬件配置"""
        return self.get_config('hardware')
    
    def get_value(self, config_type: str, key_path: str, default: Any = None) -> Any:
        """
        获取配置值，支持嵌套键路径
        
        Args:
            config_type: 配置类型 ('model', 'system', 'hardware')
            key_path: 键路径，用点号分隔，如 'training.batch_size'
            default: 默认值
        
        Returns:
            配置值
        """
        config = self.get_config(config_type)
        keys = key_path.split('.')
        
        try:
            value = config
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def update_config(self, config_type: str, key_path: str, value: Any):
        """
        更新配置值
        
        Args:
            config_type: 配置类型
            key_path: 键路径
            value: 新值
        """
        if config_type not in self._configs:
            self._configs[config_type] = {}
        
        config = self._configs[config_type]
        keys = key_path.split('.')
        
        # 导航到目标位置
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
    
    def save_config(self, config_type: str):
        """保存配置到文件"""
        config_files = {
            'model': 'model_config.yaml',
            'system': 'system_config.yaml',
            'hardware': 'hardware_config.yaml'
        }
        
        if config_type in config_files:
            config_path = self.config_dir / config_files[config_type]
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._configs[config_type], f, 
                             default_flow_style=False, allow_unicode=True)
                print(f"配置文件 {config_path} 保存成功")
            except Exception as e:
                print(f"保存配置文件 {config_path} 失败: {e}")
    
    def get_classes(self) -> list:
        """获取垃圾分类类别列表"""
        return self.get_value('model', 'classes.names', [])
    
    def get_class_categories(self) -> Dict[str, list]:
        """获取垃圾分类类别映射"""
        return self.get_value('model', 'classes.categories', {})
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.get_value('model', 'model.name', 'yolov8n')
    
    def get_default_model_path(self) -> str:
        """获取默认模型路径"""
        return self.get_value('model', 'model.default_model_path', 'models/best.pt')
    
    def get_confidence_threshold(self) -> float:
        """获取置信度阈值"""
        return self.get_value('model', 'model.confidence_threshold', 0.25)
    
    def get_web_server_config(self) -> Dict[str, Any]:
        """获取Web服务器配置"""
        return self.get_value('system', 'web_server', {})
    
    def get_camera_config(self) -> Dict[str, Any]:
        """获取摄像头配置"""
        return self.get_value('hardware', 'camera', {})
    
    def get_robot_arm_config(self) -> Dict[str, Any]:
        """获取机械臂配置"""
        return self.get_value('hardware', 'robot_arm', {})


# 全局配置加载器实例
config_loader = ConfigLoader() 