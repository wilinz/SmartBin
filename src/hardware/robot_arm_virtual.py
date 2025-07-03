#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟机械臂实现
继承RobotArmInterface，提供仿真的机械臂控制功能
用于系统测试和演示
"""

import time
import threading
import random
from typing import Dict, List, Optional
from dataclasses import dataclass

from .robot_arm_interface import (
    RobotArmInterface, 
    ArmStatus, 
    Position, 
    JointAngles,
    GrabParameters,
    ArmConfiguration
)


@dataclass
class GarbageType:
    """垃圾类型定义"""
    id: int
    name: str
    bin_position: Position
    color: str
    
    def __str__(self):
        return f"{self.name} -> {self.bin_position}"


class VirtualRobotArm(RobotArmInterface):
    """
    虚拟机械臂实现
    
    提供完整的机械臂仿真功能，包括：
    - 基础运动控制
    - 抓取释放模拟
    - 垃圾分拣逻辑
    - 统计信息记录
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化虚拟机械臂"""
        super().__init__(config)
        
        # 基础属性
        self.current_position = Position(0.0, 0.0, 200.0)  # 初始位置
        self.current_joints = JointAngles(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.home_position = Position(0.0, 0.0, 200.0)
        self.pickup_position = Position(400.0, 0.0, 100.0)
        
        # 状态变量
        self.has_object = False
        self.is_moving = False
        self.move_speed = 50.0  # 默认速度
        self.grab_force = 50.0  # 默认抓取力度
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 配置垃圾桶位置
        self._setup_garbage_bins()
        
        # 统计信息
        self.statistics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'grab_count': 0,
            'release_count': 0,
            'movement_count': 0,
            'garbage_sorted': {name: 0 for name in self.garbage_bins.keys()}
        }
        
        # 操作历史
        self.operation_history = []
        
        # 错误列表
        self.errors = []
        
        self.logger.info("🦾 虚拟机械臂已初始化")
    
    def _setup_garbage_bins(self):
        """设置垃圾桶配置"""
        self.garbage_bins = {
            'plastic': GarbageType(1, '塑料垃圾桶', Position(600.0, 200.0, 50.0), '#3B82F6'),
            'banana': GarbageType(2, '厨余垃圾桶', Position(600.0, 100.0, 50.0), '#EAB308'),
            'beverages': GarbageType(3, '饮料瓶回收桶', Position(600.0, 0.0, 50.0), '#10B981'),
            'cardboard_box': GarbageType(4, '纸盒回收桶', Position(600.0, -100.0, 50.0), '#F59E0B'),
            'chips': GarbageType(5, '零食垃圾桶', Position(600.0, -200.0, 50.0), '#EF4444'),
            'fish_bones': GarbageType(6, '厨余垃圾桶2', Position(500.0, 200.0, 50.0), '#8B5CF6'),
            'instant_noodles': GarbageType(7, '包装垃圾桶', Position(500.0, 100.0, 50.0), '#F97316'),
            'milk_box_type1': GarbageType(8, '纸盒回收桶1', Position(500.0, 0.0, 50.0), '#06B6D4'),
            'milk_box_type2': GarbageType(9, '纸盒回收桶2', Position(500.0, -100.0, 50.0), '#84CC16')
        }
    
    # ==================== 连接管理 ====================
    
    def connect(self) -> bool:
        """连接虚拟机械臂"""
        try:
            self.logger.info("🔌 连接虚拟机械臂...")
            time.sleep(0.5)  # 模拟连接时间
            
            self._is_connected = True
            self.current_status = ArmStatus.IDLE
            self.errors.clear()
            
            self.logger.info("✅ 虚拟机械臂连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 连接失败: {e}")
            self.errors.append(f"连接失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开虚拟机械臂连接"""
        try:
            self.logger.info("🔌 断开虚拟机械臂连接...")
            
            # 如果正在移动，先停止
            if self.is_moving:
                self.emergency_stop()
            
            self._is_connected = False
            self.current_status = ArmStatus.DISCONNECTED
            
            self.logger.info("✅ 虚拟机械臂已断开连接")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 断开连接失败: {e}")
            return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._is_connected
    
    # ==================== 基础控制 ====================
    
    def home(self) -> bool:
        """归位到初始位置"""
        with self._lock:
            if not self._is_connected:
                self.logger.error("机械臂未连接")
                return False
            
            try:
                self.logger.info("🏠 机械臂归位中...")
                self.current_status = ArmStatus.HOMING
                self.is_moving = True
                
                # 模拟归位移动
                self._simulate_movement(self.home_position)
                self.current_position = Position(
                    self.home_position.x, 
                    self.home_position.y, 
                    self.home_position.z
                )
                self.current_joints = JointAngles(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
                
                self.is_moving = False
                self.current_status = ArmStatus.IDLE
                self.statistics['movement_count'] += 1
                
                self.logger.info("✅ 机械臂归位完成")
                return True
                
            except Exception as e:
                self.logger.error(f"❌ 归位失败: {e}")
                self.current_status = ArmStatus.ERROR
                self.is_moving = False
                self.errors.append(f"归位失败: {e}")
                return False
    
    def emergency_stop(self) -> bool:
        """紧急停止"""
        try:
            self.logger.warning("🚨 紧急停止触发")
            self.is_moving = False
            self.current_status = ArmStatus.IDLE
            return True
        except Exception as e:
            self.logger.error(f"❌ 紧急停止失败: {e}")
            return False
    
    def reset_errors(self) -> bool:
        """重置错误状态"""
        try:
            self.errors.clear()
            if self.current_status == ArmStatus.ERROR:
                self.current_status = ArmStatus.IDLE
            self.logger.info("✅ 错误状态已重置")
            return True
        except Exception as e:
            self.logger.error(f"❌ 重置错误失败: {e}")
            return False
    
    # ==================== 运动控制 ====================
    
    def move_to_position(self, position: Position, speed: Optional[float] = None) -> bool:
        """移动到指定位置"""
        with self._lock:
            if not self._is_connected:
                self.logger.error("机械臂未连接")
                return False
            
            if self.current_status == ArmStatus.ERROR:
                self.logger.error("机械臂处于错误状态")
                return False
            
            try:
                move_speed = speed if speed is not None else self.move_speed
                self.logger.info(f"📍 移动到位置: {position}, 速度: {move_speed}")
                
                self.current_status = ArmStatus.MOVING
                self.is_moving = True
                
                # 模拟移动过程
                self._simulate_movement(position, move_speed)
                
                # 更新当前位置
                self.current_position = Position(position.x, position.y, position.z)
                
                self.is_moving = False
                self.current_status = ArmStatus.IDLE
                self.statistics['movement_count'] += 1
                
                self.logger.info("✅ 移动完成")
                return True
                
            except Exception as e:
                self.logger.error(f"❌ 移动失败: {e}")
                self.current_status = ArmStatus.ERROR
                self.is_moving = False
                self.errors.append(f"移动失败: {e}")
                return False
    
    def move_to_joints(self, angles: JointAngles, speed: Optional[float] = None) -> bool:
        """移动到指定关节角度"""
        with self._lock:
            if not self._is_connected:
                self.logger.error("机械臂未连接")
                return False
            
            try:
                move_speed = speed if speed is not None else self.move_speed
                self.logger.info(f"🦾 移动关节: {angles.to_list()}, 速度: {move_speed}")
                
                self.current_status = ArmStatus.MOVING
                self.is_moving = True
                
                # 模拟关节移动时间
                move_time = max(abs(a - b) for a, b in zip(angles.to_list(), self.current_joints.to_list())) / 50.0
                time.sleep(min(move_time, 3.0))
                
                # 更新关节角度
                self.current_joints = JointAngles(*angles.to_list())
                
                # 简单的正向运动学计算（仅用于演示）
                self.current_position = self._forward_kinematics(angles)
                
                self.is_moving = False
                self.current_status = ArmStatus.IDLE
                self.statistics['movement_count'] += 1
                
                self.logger.info("✅ 关节移动完成")
                return True
                
            except Exception as e:
                self.logger.error(f"❌ 关节移动失败: {e}")
                self.current_status = ArmStatus.ERROR
                self.is_moving = False
                self.errors.append(f"关节移动失败: {e}")
                return False
    
    def get_current_position(self) -> Optional[Position]:
        """获取当前位置"""
        if not self._is_connected:
            return None
        return Position(self.current_position.x, self.current_position.y, self.current_position.z)
    
    def get_current_joints(self) -> Optional[JointAngles]:
        """获取当前关节角度"""
        if not self._is_connected:
            return None
        return JointAngles(*self.current_joints.to_list())
    
    # ==================== 抓取控制 ====================
    
    def grab_object(self, parameters: Optional[GrabParameters] = None) -> bool:
        """抓取物体"""
        with self._lock:
            if not self._is_connected:
                self.logger.error("机械臂未连接")
                return False
            
            if self.has_object:
                self.logger.warning("机械臂已经抓取了物体")
                return False
            
            try:
                params = parameters or GrabParameters()
                self.logger.info(f"🤏 抓取物体，力度: {params.force}")
                
                self.current_status = ArmStatus.GRABBING
                time.sleep(1.0)  # 模拟抓取时间
                
                # 90%成功率的抓取模拟
                if random.random() < 0.9:
                    self.has_object = True
                    self.grab_force = params.force
                    self.statistics['grab_count'] += 1
                    self.current_status = ArmStatus.IDLE
                    self.logger.info("✅ 抓取成功")
                    return True
                else:
                    self.current_status = ArmStatus.IDLE
                    self.logger.warning("⚠️ 抓取失败 - 未检测到物体")
                    return False
                
            except Exception as e:
                self.logger.error(f"❌ 抓取失败: {e}")
                self.current_status = ArmStatus.ERROR
                self.errors.append(f"抓取失败: {e}")
                return False
    
    def release_object(self) -> bool:
        """释放物体"""
        with self._lock:
            if not self._is_connected:
                self.logger.error("机械臂未连接")
                return False
            
            if not self.has_object:
                self.logger.warning("机械臂没有抓取物体")
                return False
            
            try:
                self.logger.info("📤 释放物体...")
                self.current_status = ArmStatus.RELEASING
                time.sleep(0.5)  # 模拟释放时间
                
                self.has_object = False
                self.statistics['release_count'] += 1
                self.current_status = ArmStatus.IDLE
                
                self.logger.info("✅ 物体释放成功")
                return True
                
            except Exception as e:
                self.logger.error(f"❌ 释放失败: {e}")
                self.current_status = ArmStatus.ERROR
                self.errors.append(f"释放失败: {e}")
                return False
    
    def is_holding_object(self) -> bool:
        """检查是否正在抓取物体"""
        return self.has_object
    
    # ==================== 状态查询 ====================
    
    def get_status(self) -> Dict:
        """获取机械臂详细状态"""
        return {
            'connected': self._is_connected,
            'status': self.current_status.value,
            'current_position': self.current_position.to_dict(),
            'current_joints': self.current_joints.to_list(),
            'is_moving': self.is_moving,
            'has_object': self.has_object,
            'move_speed': self.move_speed,
            'grab_force': self.grab_force,
            'errors': self.errors.copy(),
            'temperature': self._get_simulated_temperature(),
            'load': self._get_simulated_load()
        }
    
    def get_configuration(self) -> ArmConfiguration:
        """获取机械臂配置"""
        return ArmConfiguration(
            max_reach=800.0,
            max_payload=5.0,
            degrees_of_freedom=6,
            max_speed=100.0,
            acceleration=50.0,
            precision=0.1
        )
    
    # ==================== 高级功能 ====================
    
    def sort_garbage(self, garbage_type: str) -> bool:
        """垃圾分拣操作"""
        with self._lock:
            if not self._is_connected:
                self.logger.error("机械臂未连接")
                return False
            
            if garbage_type not in self.garbage_bins:
                self.logger.error(f"未知的垃圾类型: {garbage_type}")
                return False
            
            # 检查当前状态，确保不在执行其他操作
            if self.current_status != ArmStatus.IDLE:
                self.logger.error(f"机械臂正忙，当前状态: {self.current_status.value}")
                return False
            
            try:
                garbage_info = self.garbage_bins[garbage_type]
                self.logger.info(f"🗑️ 开始分拣垃圾: {garbage_info}")
                
                # 立即设置状态为抓取中，防止重复调用
                self.current_status = ArmStatus.GRABBING
                
                # 1. 移动到拾取位置
                if not self.move_to_position(self.pickup_position):
                    return False
                
                # 2. 抓取物体
                if not self.grab_object():
                    return False
                
                # 3. 移动到对应垃圾桶
                if not self.move_to_position(garbage_info.bin_position):
                    return False
                
                # 4. 释放物体
                if not self.release_object():
                    return False
                
                # 5. 归位
                if not self.home():
                    return False
                
                # 更新统计信息
                self.statistics['total_operations'] += 1
                self.statistics['successful_operations'] += 1
                self.statistics['garbage_sorted'][garbage_type] += 1
                
                # 记录操作历史
                operation = {
                    'timestamp': time.time(),
                    'garbage_type': garbage_type,
                    'status': 'success',
                    'position': garbage_info.bin_position.to_dict()
                }
                self.operation_history.append(operation)
                
                self.logger.info(f"✅ 垃圾分拣完成: {garbage_info.name}")
                return True
                
            except Exception as e:
                self.logger.error(f"❌ 垃圾分拣失败: {e}")
                self.statistics['total_operations'] += 1
                self.statistics['failed_operations'] += 1
                
                # 记录失败操作
                operation = {
                    'timestamp': time.time(),
                    'garbage_type': garbage_type,
                    'status': 'failed',
                    'error': str(e)
                }
                self.operation_history.append(operation)
                
                # 重置状态为ERROR，但确保不影响后续操作
                self.current_status = ArmStatus.ERROR
                self.errors.append(f"分拣失败: {e}")
                return False
            
            finally:
                # 确保无论成功还是失败，都清理状态（如果不是ERROR状态）
                if self.current_status not in [ArmStatus.IDLE, ArmStatus.ERROR]:
                    self.current_status = ArmStatus.IDLE
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return self.statistics.copy()
    
    def get_operation_history(self, limit: int = 10) -> List[Dict]:
        """获取操作历史"""
        return self.operation_history[-limit:] if limit > 0 else self.operation_history
    
    def reset_statistics(self) -> bool:
        """重置统计信息"""
        try:
            self.statistics = {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'grab_count': 0,
                'release_count': 0,
                'movement_count': 0,
                'garbage_sorted': {name: 0 for name in self.garbage_bins.keys()}
            }
            self.operation_history.clear()
            self.logger.info("📊 统计信息已重置")
            return True
        except Exception as e:
            self.logger.error(f"❌ 重置统计信息失败: {e}")
            return False
    
    def get_garbage_bins_info(self) -> Dict:
        """获取垃圾桶信息"""
        return {
            name: {
                'id': info.id,
                'name': info.name,
                'position': info.bin_position.to_dict(),
                'color': info.color,
                'sorted_count': self.statistics['garbage_sorted'][name]
            }
            for name, info in self.garbage_bins.items()
        }
    
    # ==================== 私有辅助方法 ====================
    
    def _simulate_movement(self, target_position: Position, speed: float = 50.0):
        """模拟机械臂移动"""
        # 计算移动距离
        distance = self._calculate_distance(self.current_position, target_position)
        
        # 计算移动时间（基于速度）
        move_time = distance / (speed * 10)  # 简化的时间计算
        
        # 模拟移动过程
        time.sleep(min(move_time, 3.0))  # 最大3秒
        
        self.logger.debug(f"移动距离: {distance:.2f}mm, 用时: {move_time:.2f}s")
    
    def _calculate_distance(self, pos1: Position, pos2: Position) -> float:
        """计算两点间距离"""
        return ((pos1.x - pos2.x) ** 2 + 
                (pos1.y - pos2.y) ** 2 + 
                (pos1.z - pos2.z) ** 2) ** 0.5
    
    def _forward_kinematics(self, angles: JointAngles) -> Position:
        """简化的正向运动学计算"""
        # 这里是简化的计算，实际应该根据机械臂的DH参数计算
        x = 400 * (angles.j1 / 90.0) + 100
        y = 300 * (angles.j2 / 90.0)
        z = 200 + 150 * (angles.j3 / 90.0)
        return Position(x, y, z)
    
    def _get_simulated_temperature(self) -> Dict:
        """获取模拟温度数据"""
        return {
            'motor_1': 25 + random.uniform(-2, 5),
            'motor_2': 28 + random.uniform(-2, 5),
            'motor_3': 24 + random.uniform(-2, 5),
            'controller': 35 + random.uniform(-3, 8)
        }
    
    def _get_simulated_load(self) -> Dict:
        """获取模拟负载数据"""
        base_load = 0.5 if self.has_object else 0.1
        return {
            'current_load': base_load + random.uniform(-0.1, 0.2),
            'max_load': 5.0,
            'percentage': (base_load / 5.0) * 100
        }
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, '_is_connected') and self._is_connected:
            self.disconnect()


# ==================== 向后兼容性 ====================

# 保持与原有代码的兼容性
VirtualRobotArmController = VirtualRobotArm 