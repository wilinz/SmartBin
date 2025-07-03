#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机械臂抽象接口定义
提供标准化的机械臂控制接口，支持第三方实现
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)


class ArmStatus(Enum):
    """机械臂状态枚举"""
    IDLE = "idle"                # 空闲
    MOVING = "moving"            # 移动中
    GRABBING = "grabbing"        # 抓取中
    RELEASING = "releasing"      # 释放中
    ERROR = "error"              # 错误状态
    HOMING = "homing"            # 归位中
    DISCONNECTED = "disconnected" # 未连接


@dataclass
class Position:
    """3D位置坐标"""
    x: float
    y: float
    z: float
    
    def __str__(self):
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {'x': self.x, 'y': self.y, 'z': self.z}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        """从字典创建位置"""
        return cls(x=data['x'], y=data['y'], z=data['z'])


@dataclass
class JointAngles:
    """关节角度（6轴机械臂）"""
    j1: float  # 基座旋转
    j2: float  # 肩部
    j3: float  # 肘部
    j4: float  # 腕部旋转
    j5: float  # 腕部俯仰
    j6: float  # 末端旋转
    
    def to_list(self) -> List[float]:
        """转换为列表"""
        return [self.j1, self.j2, self.j3, self.j4, self.j5, self.j6]
    
    @classmethod
    def from_list(cls, angles: List[float]) -> 'JointAngles':
        """从列表创建关节角度"""
        if len(angles) != 6:
            raise ValueError("需要6个关节角度")
        return cls(*angles)


@dataclass
class GrabParameters:
    """抓取参数"""
    force: float = 50.0          # 抓取力度 (0-100)
    speed: float = 50.0          # 抓取速度 (0-100)
    position_tolerance: float = 2.0  # 位置容差 (mm)
    timeout: float = 5.0         # 超时时间 (秒)


@dataclass
class ArmConfiguration:
    """机械臂配置参数"""
    max_reach: float = 800.0     # 最大工作半径 (mm)
    max_payload: float = 5.0     # 最大负载 (kg)
    degrees_of_freedom: int = 6  # 自由度
    max_speed: float = 100.0     # 最大移动速度 (mm/s)
    acceleration: float = 50.0   # 加速度 (mm/s²)
    precision: float = 0.1       # 定位精度 (mm)


class RobotArmInterface(ABC):
    """
    机械臂抽象接口类
    
    第三方厂商需要继承此类并实现所有抽象方法
    以提供具体的机械臂控制功能
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化机械臂接口
        
        Args:
            config: 配置参数字典
        """
        self.config = config or {}
        self._is_connected = False
        self.current_status = ArmStatus.DISCONNECTED
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    # ==================== 连接管理 ====================
    
    @abstractmethod
    def connect(self) -> bool:
        """
        连接机械臂
        
        Returns:
            bool: 连接成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开机械臂连接
        
        Returns:
            bool: 断开成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查连接状态
        
        Returns:
            bool: 已连接返回True，未连接返回False
        """
        pass
    
    # ==================== 基础控制 ====================
    
    @abstractmethod
    def home(self) -> bool:
        """
        机械臂归位到初始位置
        
        Returns:
            bool: 归位成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def emergency_stop(self) -> bool:
        """
        紧急停止所有动作
        
        Returns:
            bool: 停止成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def reset_errors(self) -> bool:
        """
        重置错误状态
        
        Returns:
            bool: 重置成功返回True，失败返回False
        """
        pass
    
    # ==================== 运动控制 ====================
    
    @abstractmethod
    def move_to_position(self, position: Position, speed: Optional[float] = None) -> bool:
        """
        移动到指定的笛卡尔坐标位置
        
        Args:
            position: 目标位置
            speed: 移动速度 (0-100)，None使用默认速度
            
        Returns:
            bool: 移动成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def move_to_joints(self, angles: JointAngles, speed: Optional[float] = None) -> bool:
        """
        移动到指定的关节角度
        
        Args:
            angles: 目标关节角度
            speed: 移动速度 (0-100)，None使用默认速度
            
        Returns:
            bool: 移动成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def get_current_position(self) -> Optional[Position]:
        """
        获取当前笛卡尔坐标位置
        
        Returns:
            Position: 当前位置，获取失败返回None
        """
        pass
    
    @abstractmethod
    def get_current_joints(self) -> Optional[JointAngles]:
        """
        获取当前关节角度
        
        Returns:
            JointAngles: 当前关节角度，获取失败返回None
        """
        pass
    
    # ==================== 抓取控制 ====================
    
    @abstractmethod
    def grab_object(self, parameters: Optional[GrabParameters] = None) -> bool:
        """
        抓取物体
        
        Args:
            parameters: 抓取参数，None使用默认参数
            
        Returns:
            bool: 抓取成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def release_object(self) -> bool:
        """
        释放物体
        
        Returns:
            bool: 释放成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def is_holding_object(self) -> bool:
        """
        检查是否正在抓取物体
        
        Returns:
            bool: 正在抓取返回True，否则返回False
        """
        pass
    
    # ==================== 状态查询 ====================
    
    @abstractmethod
    def get_status(self) -> Dict:
        """
        获取机械臂详细状态
        
        Returns:
            Dict: 包含状态信息的字典
                - status: ArmStatus枚举值
                - position: 当前位置
                - joints: 当前关节角度
                - is_moving: 是否在移动
                - has_object: 是否抓取物体
                - errors: 错误列表
                - temperature: 温度信息（如果支持）
                - load: 负载信息（如果支持）
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> ArmConfiguration:
        """
        获取机械臂配置信息
        
        Returns:
            ArmConfiguration: 机械臂配置
        """
        pass
    
    # ==================== 高级功能 ====================
    
    def move_linear(self, target_position: Position, speed: Optional[float] = None) -> bool:
        """
        线性移动到目标位置（直线轨迹）
        
        默认实现调用move_to_position，子类可以重写提供更精确的线性插补
        
        Args:
            target_position: 目标位置
            speed: 移动速度
            
        Returns:
            bool: 移动成功返回True，失败返回False
        """
        return self.move_to_position(target_position, speed)
    
    def move_circular(self, via_position: Position, target_position: Position, 
                     speed: Optional[float] = None) -> bool:
        """
        圆弧移动（经过中间点到目标位置）
        
        默认实现依次移动到两个位置，子类可以重写提供真正的圆弧插补
        
        Args:
            via_position: 中间点位置
            target_position: 目标位置
            speed: 移动速度
            
        Returns:
            bool: 移动成功返回True，失败返回False
        """
        if not self.move_to_position(via_position, speed):
            return False
        return self.move_to_position(target_position, speed)
    
    def calibrate(self) -> bool:
        """
        机械臂校准
        
        默认实现返回True，子类可以重写提供具体的校准功能
        
        Returns:
            bool: 校准成功返回True，失败返回False
        """
        self.logger.info("使用默认校准实现")
        return True
    
    def set_speed(self, speed: float) -> bool:
        """
        设置全局移动速度
        
        Args:
            speed: 速度值 (0-100)
            
        Returns:
            bool: 设置成功返回True，失败返回False
        """
        if not 0 <= speed <= 100:
            self.logger.error(f"无效的速度值: {speed}")
            return False
        return True
    
    def set_acceleration(self, acceleration: float) -> bool:
        """
        设置全局加速度
        
        Args:
            acceleration: 加速度值
            
        Returns:
            bool: 设置成功返回True，失败返回False
        """
        return True
    
    # ==================== 工具支持 ====================
    
    def enable_tool(self, tool_id: int) -> bool:
        """
        启用工具（如气动夹爪）
        
        Args:
            tool_id: 工具ID
            
        Returns:
            bool: 启用成功返回True，失败返回False
        """
        return True
    
    def disable_tool(self, tool_id: int) -> bool:
        """
        禁用工具
        
        Args:
            tool_id: 工具ID
            
        Returns:
            bool: 禁用成功返回True，失败返回False
        """
        return True
    
    # ==================== 安全功能 ====================
    
    def set_safety_limits(self, limits: Dict) -> bool:
        """
        设置安全限制
        
        Args:
            limits: 限制参数字典
                - max_speed: 最大速度
                - max_force: 最大力度
                - workspace: 工作空间限制
                
        Returns:
            bool: 设置成功返回True，失败返回False
        """
        return True
    
    def get_safety_status(self) -> Dict:
        """
        获取安全状态
        
        Returns:
            Dict: 安全状态信息
        """
        return {
            'is_safe': True,
            'violations': [],
            'emergency_stop_active': False
        }
    
    # ==================== 数据记录 ====================
    
    def start_recording(self, filename: str) -> bool:
        """
        开始记录运动轨迹
        
        Args:
            filename: 记录文件名
            
        Returns:
            bool: 开始记录成功返回True，失败返回False
        """
        return True
    
    def stop_recording(self) -> bool:
        """
        停止记录轨迹
        
        Returns:
            bool: 停止记录成功返回True，失败返回False
        """
        return True
    
    def replay_trajectory(self, filename: str) -> bool:
        """
        重放记录的轨迹
        
        Args:
            filename: 轨迹文件名
            
        Returns:
            bool: 重放成功返回True，失败返回False
        """
        return True


# ==================== 辅助函数 ====================

def create_robot_arm(arm_type: str, config: Optional[Dict] = None) -> Optional[RobotArmInterface]:
    """
    工厂函数：根据类型创建机械臂实例
    
    Args:
        arm_type: 机械臂类型 ('virtual', 'ur', 'kuka', 'abb', ...)
        config: 配置参数
        
    Returns:
        RobotArmInterface: 机械臂实例，创建失败返回None
    """
    try:
        if arm_type.lower() == 'virtual':
            from .robot_arm_virtual import VirtualRobotArm
            return VirtualRobotArm(config)
        elif arm_type.lower() == 'ur':
            # 示例：Universal Robots机械臂
            try:
                from .robot_arm_ur import URRobotArm
                return URRobotArm(config)
            except ImportError:
                logger.error("UR机械臂驱动未安装")
                return None
        elif arm_type.lower() == 'kuka':
            # 示例：KUKA机械臂
            try:
                from .robot_arm_kuka import KukaRobotArm
                return KukaRobotArm(config)
            except ImportError:
                logger.error("KUKA机械臂驱动未安装")
                return None
        else:
            logger.error(f"不支持的机械臂类型: {arm_type}")
            return None
    except Exception as e:
        logger.error(f"创建机械臂实例失败: {e}")
        return None


# 导出接口
__all__ = [
    'RobotArmInterface',
    'ArmStatus',
    'Position', 
    'JointAngles',
    'GrabParameters',
    'ArmConfiguration',
    'create_robot_arm'
] 