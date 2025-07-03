#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机械臂控制模块 - 统一入口
基于抽象接口架构，支持多种机械臂厂商的实现
提供向后兼容的接口包装器
"""

import logging
from typing import Dict, List, Optional

# 导入抽象接口
from .robot_arm_interface import (
    RobotArmInterface,
    ArmStatus,
    Position, 
    JointAngles,
    GrabParameters,
    ArmConfiguration,
    create_robot_arm
)

# 导入具体实现
from .robot_arm_virtual import VirtualRobotArm

# 设置日志记录器
logger = logging.getLogger(__name__)


class RobotArmController:
    """
    机械臂控制器包装器
    
    提供统一的机械臂控制接口，支持多种机械臂类型
    保持与原有代码的向后兼容性
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化机械臂控制器
        
        Args:
            config: 配置参数，包含：
                - arm_type: 机械臂类型 ('virtual', 'ur', 'kuka', 等)
                - 其他机械臂特定配置
        """
        self.config = config or {}
        self.arm_type = self.config.get('arm_type', 'virtual')
        
        # 创建具体的机械臂实例
        self._arm_instance = self._create_arm_instance()
        
        if self._arm_instance is None:
            logger.error(f"❌ 无法创建机械臂实例: {self.arm_type}")
            raise RuntimeError(f"不支持的机械臂类型: {self.arm_type}")
        
        logger.info(f"✅ 机械臂控制器初始化完成: {self.arm_type}")
    
    def _create_arm_instance(self) -> Optional[RobotArmInterface]:
        """创建机械臂实例"""
        try:
            if self.arm_type.lower() == 'virtual':
                return VirtualRobotArm(self.config)
            else:
                # 使用工厂函数创建其他类型的机械臂
                return create_robot_arm(self.arm_type, self.config)
        except Exception as e:
            logger.error(f"创建机械臂实例失败: {e}")
            return None
    
    # ==================== 向后兼容接口 ====================
    
    @property
    def is_connected(self) -> bool:
        """检查连接状态（属性访问）"""
        if not self._arm_instance:
            return False
        try:
            return self._arm_instance.is_connected()
        except Exception:
            # 如果调用方法失败，尝试属性访问
            return getattr(self._arm_instance, '__dict__', {}).get('is_connected', False)
    
    @property
    def status(self) -> str:
        """获取当前状态（属性访问）"""
        if not self._arm_instance:
            return ArmStatus.DISCONNECTED.value
        status = self._arm_instance.get_status()
        return status.get('status', ArmStatus.DISCONNECTED.value)
    
    @property
    def current_position(self) -> Optional[Position]:
        """获取当前位置（属性访问）"""
        return self._arm_instance.get_current_position() if self._arm_instance else None
    
    @property
    def has_object(self) -> bool:
        """检查是否抓取物体（属性访问）"""
        return self._arm_instance.is_holding_object() if self._arm_instance else False
    
    def connect(self) -> bool:
        """连接机械臂"""
        return self._arm_instance.connect() if self._arm_instance else False
    
    def disconnect(self) -> bool:
        """断开机械臂连接"""
        return self._arm_instance.disconnect() if self._arm_instance else False
    
    def home(self) -> bool:
        """机械臂归位"""
        return self._arm_instance.home() if self._arm_instance else False
    
    def move_to_position(self, position: Position) -> bool:
        """移动到指定位置"""
        return self._arm_instance.move_to_position(position) if self._arm_instance else False
    
    def grab_object(self, target_class: Optional[str] = None, confidence: Optional[float] = None, 
                   position: Optional[List[float]] = None, bbox: Optional[List[float]] = None) -> bool:
        """
        抓取物体
        
        支持智能抓取和基础抓取两种模式：
        1. 智能抓取：当提供target_class时，直接进行垃圾分拣
        2. 基础抓取：仅进行抓取动作
        """
        if not self._arm_instance:
            return False
        
        # 智能抓取模式：直接调用垃圾分拣
        if target_class and hasattr(self._arm_instance, 'sort_garbage'):
            logger.info(f"🎯 智能抓取模式: {target_class}")
            if confidence:
                logger.info(f"   置信度: {confidence:.2f}")
            if position:
                logger.info(f"   位置: ({position[0]:.1f}, {position[1]:.1f})")
            if bbox:
                logger.info(f"   检测框: [{bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}]")
            
            return self._arm_instance.sort_garbage(target_class)
        
        # 基础抓取模式
        return self._arm_instance.grab_object()
    
    def release_object(self) -> bool:
        """释放物体"""
        return self._arm_instance.release_object() if self._arm_instance else False
    
    def emergency_stop(self) -> bool:
        """紧急停止"""
        return self._arm_instance.emergency_stop() if self._arm_instance else False
    
    def get_status(self) -> Dict:
        """获取机械臂状态"""
        if not self._arm_instance:
            return {
                'connected': False,
                'status': ArmStatus.DISCONNECTED.value,
                'current_position': {'x': 0, 'y': 0, 'z': 0},
                'has_object': False,
                'errors': ['机械臂实例未创建']
            }
        
        return self._arm_instance.get_status()
    
    # ==================== 扩展功能接口 ====================
    
    def move_to_joints(self, angles: JointAngles, speed: Optional[float] = None) -> bool:
        """移动到指定关节角度"""
        return self._arm_instance.move_to_joints(angles, speed) if self._arm_instance else False
    
    def get_current_joints(self) -> Optional[JointAngles]:
        """获取当前关节角度"""
        return self._arm_instance.get_current_joints() if self._arm_instance else None
    
    def get_configuration(self) -> Optional[ArmConfiguration]:
        """获取机械臂配置"""
        return self._arm_instance.get_configuration() if self._arm_instance else None
    
    def set_speed(self, speed: float) -> bool:
        """设置移动速度"""
        return self._arm_instance.set_speed(speed) if self._arm_instance else False
    
    def calibrate(self) -> bool:
        """机械臂校准"""
        return self._arm_instance.calibrate() if self._arm_instance else False
    
    # ==================== 虚拟机械臂专用接口 ====================
    
    def sort_garbage(self, garbage_type: str) -> bool:
        """垃圾分拣操作（虚拟机械臂专用）"""
        if hasattr(self._arm_instance, 'sort_garbage'):
            return self._arm_instance.sort_garbage(garbage_type)
        else:
            logger.warning(f"机械臂类型 {self.arm_type} 不支持垃圾分拣功能")
            return False
    
    def get_statistics(self) -> Dict:
        """获取统计信息（虚拟机械臂专用）"""
        if hasattr(self._arm_instance, 'get_statistics'):
            return self._arm_instance.get_statistics()
        else:
            return {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'message': f'机械臂类型 {self.arm_type} 不支持统计功能'
            }
    
    def get_operation_history(self, limit: int = 10) -> List[Dict]:
        """获取操作历史（虚拟机械臂专用）"""
        if hasattr(self._arm_instance, 'get_operation_history'):
            return self._arm_instance.get_operation_history(limit)
        else:
            return []
    
    def reset_statistics(self) -> bool:
        """重置统计信息（虚拟机械臂专用）"""
        if hasattr(self._arm_instance, 'reset_statistics'):
            return self._arm_instance.reset_statistics()
        else:
            logger.warning(f"机械臂类型 {self.arm_type} 不支持统计重置功能")
            return False
    
    def get_garbage_bins_info(self) -> Dict:
        """获取垃圾桶信息（虚拟机械臂专用）"""
        if hasattr(self._arm_instance, 'get_garbage_bins_info'):
            return self._arm_instance.get_garbage_bins_info()
        else:
            return {}
    
    # ==================== 直接访问底层实例 ====================
    
    def get_arm_instance(self) -> Optional[RobotArmInterface]:
        """获取底层机械臂实例（高级用法）"""
        return self._arm_instance
    
    def switch_arm_type(self, new_arm_type: str, config: Optional[Dict] = None) -> bool:
        """
        切换机械臂类型（热切换）
        
        Args:
            new_arm_type: 新的机械臂类型
            config: 新的配置参数
            
        Returns:
            bool: 切换成功返回True
        """
        try:
            # 断开当前连接  
            if self._arm_instance:
                try:
                    # 使用属性访问方式检查连接状态
                    if hasattr(self._arm_instance, '__dict__') and self._arm_instance.__dict__.get('is_connected', False):
                        self._arm_instance.disconnect()
                except Exception as e:
                    logger.warning(f"断开连接时出错: {e}")
            
            # 更新配置
            self.arm_type = new_arm_type
            if config:
                self.config.update(config)
            self.config['arm_type'] = new_arm_type
            
            # 创建新实例
            new_instance = self._create_arm_instance()
            if new_instance:
                self._arm_instance = new_instance
                logger.info(f"✅ 机械臂类型切换成功: {new_arm_type}")
                return True
            else:
                logger.error(f"❌ 机械臂类型切换失败: {new_arm_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 切换机械臂类型时发生错误: {e}")
            return False
    
    def __getattr__(self, name):
        """
        属性代理：将未定义的属性和方法转发给底层机械臂实例
        这提供了最大的灵活性，允许访问特定机械臂的专有功能
        """
        if self._arm_instance and hasattr(self._arm_instance, name):
            return getattr(self._arm_instance, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' 和底层机械臂都没有属性 '{name}'")
    
    def __del__(self):
        """析构函数"""
        try:
            if self._arm_instance:
                # 使用属性访问方式，避免方法调用问题
                if hasattr(self._arm_instance, '__dict__') and self._arm_instance.__dict__.get('is_connected', False):
                    self._arm_instance.disconnect()
        except Exception:
            # 在析构函数中忽略所有异常
            pass


# ==================== 向后兼容性别名 ====================

# 保持与原有代码的完全兼容性
VirtualRobotArmController = RobotArmController

# 创建全局实例（兼容原有代码）
robot_arm_controller = RobotArmController({'arm_type': 'virtual'})


# ==================== 工厂函数 ====================

def create_robot_arm_controller(arm_type: str = 'virtual', config: Optional[Dict] = None) -> RobotArmController:
    """
    工厂函数：创建机械臂控制器
    
    Args:
        arm_type: 机械臂类型 ('virtual', 'ur', 'kuka', 等)
        config: 配置参数
        
    Returns:
        RobotArmController: 机械臂控制器实例
    """
    final_config = config or {}
    final_config['arm_type'] = arm_type
    return RobotArmController(final_config)


# ==================== 便捷函数 ====================

def get_supported_arm_types() -> List[str]:
    """获取支持的机械臂类型列表"""
    return ['virtual', 'ur', 'kuka', 'abb']

def get_arm_type_info(arm_type: str) -> Dict:
    """获取机械臂类型信息"""
    info_map = {
        'virtual': {
            'name': '虚拟机械臂',
            'description': '用于测试和演示的仿真机械臂',
            'features': ['垃圾分拣', '统计记录', '操作历史'],
            'config_required': False
        },
        'ur': {
            'name': 'Universal Robots',
            'description': 'UR系列协作机械臂',
            'features': ['TCP通信', '实时控制', '力控制'],
            'config_required': True,
            'config_fields': ['host', 'port']
        },
        'kuka': {
            'name': 'KUKA机械臂',
            'description': 'KUKA工业机械臂',
            'features': ['KRL编程', '高精度', '重载能力'],
            'config_required': True,
            'config_fields': ['host', 'port', 'krl_config']
        }
    }
    
    return info_map.get(arm_type, {
        'name': '未知类型',
        'description': '不支持的机械臂类型',
        'features': [],
        'config_required': False
    })


# ==================== 导出接口 ====================

__all__ = [
    # 主要类
    'RobotArmController',
    'VirtualRobotArmController',  # 向后兼容别名
    
    # 全局实例
    'robot_arm_controller',
    
    # 工厂函数
    'create_robot_arm_controller',
    
    # 便捷函数
    'get_supported_arm_types',
    'get_arm_type_info',
    
    # 从抽象接口导入的类型
    'RobotArmInterface',
    'ArmStatus',
    'Position',
    'JointAngles', 
    'GrabParameters',
    'ArmConfiguration'
] 