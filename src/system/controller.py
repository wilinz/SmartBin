#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统主控制器
协调各个模块的工作，实现完整的垃圾分拣流程
"""

import time
import logging
import threading
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from ..utils.config_loader import config_loader
from ..models.detector import GarbageDetector
from ..hardware.camera import CameraController
from ..hardware.robot_arm import RobotArmController
from .scheduler import TaskScheduler


class SystemState(Enum):
    """系统状态枚举"""
    IDLE = "idle"                    # 空闲
    DETECTING = "detecting"          # 检测中
    SORTING = "sorting"              # 分拣中
    ERROR = "error"                  # 错误
    MAINTENANCE = "maintenance"      # 维护模式


@dataclass
class DetectionTask:
    """检测任务"""
    id: str
    image: Any
    timestamp: float
    results: Optional[Dict] = None
    status: str = "pending"


@dataclass
class SortingTask:
    """分拣任务"""
    id: str
    detections: List[Dict]
    timestamp: float
    pickup_position: str
    target_category: str
    status: str = "pending"


class SystemController:
    """系统主控制器"""
    
    def __init__(self):
        self.config = config_loader.get_system_config()
        self.hardware_config = config_loader.get_hardware_config()
        
        # 初始化组件
        self.detector = None
        self.camera = None
        self.robot_arm = None
        self.scheduler = TaskScheduler()
        
        # 系统状态
        self.state = SystemState.IDLE
        self.is_running = False
        self.auto_mode = False
        
        # 任务队列
        self.detection_tasks = []
        self.sorting_tasks = []
        
        # 线程锁
        self.state_lock = threading.Lock()
        self.task_lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            'total_detections': 0,
            'total_sortings': 0,
            'success_rate': 0.0,
            'uptime': 0.0,
            'last_error': None
        }
        
        # 回调函数
        self.callbacks = {
            'on_detection': [],
            'on_sorting': [],
            'on_error': [],
            'on_state_change': []
        }
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 主控制线程
        self.control_thread = None
        self.start_time = time.time()
    
    def initialize(self) -> bool:
        """
        初始化系统
        
        Returns:
            初始化是否成功
        """
        try:
            self.logger.info("开始初始化系统...")
            
            # 初始化检测器
            self.logger.info("初始化检测器...")
            self.detector = GarbageDetector()  # 默认会自动加载默认模型
            
            # 初始化摄像头
            self.logger.info("初始化摄像头...")
            self.camera = CameraController()
            if not self.camera.start():
                raise Exception("摄像头初始化失败")
            
            # 初始化机械臂
            if self.hardware_config.get('robot_arm', {}).get('enabled', True):
                self.logger.info("初始化机械臂...")
                self.robot_arm = RobotArmController()
                if not self.robot_arm.connect():
                    self.logger.warning("机械臂连接失败，将在无机械臂模式下运行")
            
            self.logger.info("系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"系统初始化失败: {e}")
            self._set_error_state(str(e))
            return False
    
    def start(self) -> bool:
        """
        启动系统
        
        Returns:
            启动是否成功
        """
        if self.is_running:
            self.logger.warning("系统已经在运行中")
            return True
        
        try:
            if not self.initialize():
                return False
            
            self.is_running = True
            self._set_state(SystemState.IDLE)
            
            # 启动主控制线程
            self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
            self.control_thread.start()
            
            self.logger.info("系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            self._set_error_state(str(e))
            return False
    
    def stop(self):
        """停止系统"""
        try:
            self.logger.info("正在停止系统...")
            
            self.is_running = False
            self.auto_mode = False
            
            # 等待控制线程结束
            if self.control_thread and self.control_thread.is_alive():
                self.control_thread.join(timeout=5.0)
            
            # 停止硬件
            if self.camera:
                self.camera.stop()
            
            if self.robot_arm:
                self.robot_arm.disconnect()
            
            self._set_state(SystemState.IDLE)
            self.logger.info("系统已停止")
            
        except Exception as e:
            self.logger.error(f"停止系统失败: {e}")
    
    def _control_loop(self):
        """主控制循环"""
        while self.is_running:
            try:
                if self.state == SystemState.ERROR:
                    time.sleep(1.0)
                    continue
                
                # 自动模式下的处理逻辑
                if self.auto_mode and self.state == SystemState.IDLE:
                    self._auto_mode_cycle()
                
                # 处理检测任务
                self._process_detection_tasks()
                
                # 处理分拣任务
                self._process_sorting_tasks()
                
                # 更新统计信息
                self._update_stats()
                
                time.sleep(0.1)  # 控制循环频率
                
            except Exception as e:
                self.logger.error(f"控制循环错误: {e}")
                self._set_error_state(str(e))
                time.sleep(1.0)
    
    def _auto_mode_cycle(self):
        """自动模式周期"""
        try:
            # 获取摄像头图像
            frame = self.camera.get_frame()
            if frame is None:
                return
            
            # 创建检测任务
            task = DetectionTask(
                id=f"auto_{int(time.time() * 1000)}",
                image=frame,
                timestamp=time.time()
            )
            
            with self.task_lock:
                self.detection_tasks.append(task)
            
        except Exception as e:
            self.logger.error(f"自动模式周期错误: {e}")
    
    def _process_detection_tasks(self):
        """处理检测任务"""
        with self.task_lock:
            if not self.detection_tasks:
                return
            
            task = self.detection_tasks.pop(0)
        
        try:
            if self.detector is None or self.detector.model is None:
                task.status = "failed"
                self.logger.warning("检测器未准备就绪")
                return
            
            # 执行检测
            self._set_state(SystemState.DETECTING)
            results = self.detector.detect(task.image)
            
            task.results = results
            task.status = "completed"
            
            # 触发检测完成回调
            self._trigger_callbacks('on_detection', task)
            
            # 如果检测到垃圾，创建分拣任务
            if results['total_detections'] > 0:
                self._create_sorting_tasks(task)
            
            self.stats['total_detections'] += 1
            
        except Exception as e:
            self.logger.error(f"检测任务失败: {e}")
            task.status = "failed"
        finally:
            if self.state == SystemState.DETECTING:
                self._set_state(SystemState.IDLE)
    
    def _create_sorting_tasks(self, detection_task: DetectionTask):
        """根据检测结果创建分拣任务"""
        try:
            results = detection_task.results
            
            # 按照类别分组检测结果
            category_groups = {}
            for detection in results['detections']:
                category = detection['category']
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(detection)
            
            # 为每个类别创建分拣任务
            for category, detections in category_groups.items():
                if category == 'unknown':
                    continue
                
                # 选择置信度最高的检测结果
                best_detection = max(detections, key=lambda x: x['confidence'])
                
                sorting_task = SortingTask(
                    id=f"sort_{detection_task.id}_{category}",
                    detections=[best_detection],
                    timestamp=time.time(),
                    pickup_position=self._calculate_pickup_position(best_detection),
                    target_category=category
                )
                
                with self.task_lock:
                    self.sorting_tasks.append(sorting_task)
                
        except Exception as e:
            self.logger.error(f"创建分拣任务失败: {e}")
    
    def _calculate_pickup_position(self, detection: Dict) -> str:
        """计算拾取位置"""
        # 简化版本：根据检测框的位置决定拾取位置
        center_x = detection['center'][0]
        
        # 假设摄像头视野分为3个区域
        if center_x < 0.33:
            return "position_1"
        elif center_x < 0.66:
            return "position_2"
        else:
            return "position_3"
    
    def _process_sorting_tasks(self):
        """处理分拣任务"""
        if not self.robot_arm or not self.robot_arm.is_connected():
            return
        
        with self.task_lock:
            if not self.sorting_tasks:
                return
            
            task = self.sorting_tasks.pop(0)
        
        try:
            self._set_state(SystemState.SORTING)
            
            # 执行分拣动作
            success = self._execute_sorting(task)
            
            task.status = "completed" if success else "failed"
            
            # 触发分拣完成回调
            self._trigger_callbacks('on_sorting', task)
            
            if success:
                self.stats['total_sortings'] += 1
            
        except Exception as e:
            self.logger.error(f"分拣任务失败: {e}")
            task.status = "failed"
        finally:
            if self.state == SystemState.SORTING:
                self._set_state(SystemState.IDLE)
    
    def _execute_sorting(self, task: SortingTask) -> bool:
        """执行分拣动作"""
        try:
            # 移动到拾取位置
            pickup_pos = self.robot_arm.get_position(task.pickup_position)
            if not self.robot_arm.move_to_position(pickup_pos['x'], pickup_pos['y'], pickup_pos['z']):
                return False
            
            # 夹取物品
            if not self.robot_arm.grip():
                return False
            
            # 移动到目标位置
            drop_pos = self.robot_arm.get_drop_position(task.target_category)
            if not self.robot_arm.move_to_position(drop_pos['x'], drop_pos['y'], drop_pos['z']):
                return False
            
            # 释放物品
            if not self.robot_arm.release():
                return False
            
            # 返回初始位置
            home_pos = self.robot_arm.get_home_position()
            self.robot_arm.move_to_position(home_pos['x'], home_pos['y'], home_pos['z'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"执行分拣动作失败: {e}")
            return False
    
    def _set_state(self, new_state: SystemState):
        """设置系统状态"""
        with self.state_lock:
            if self.state != new_state:
                old_state = self.state
                self.state = new_state
                self.logger.info(f"系统状态变更: {old_state.value} -> {new_state.value}")
                self._trigger_callbacks('on_state_change', {'old': old_state, 'new': new_state})
    
    def _set_error_state(self, error_message: str):
        """设置错误状态"""
        self.stats['last_error'] = {
            'message': error_message,
            'timestamp': time.time()
        }
        self._set_state(SystemState.ERROR)
        self._trigger_callbacks('on_error', error_message)
    
    def _update_stats(self):
        """更新统计信息"""
        self.stats['uptime'] = time.time() - self.start_time
        
        total_tasks = self.stats['total_detections']
        if total_tasks > 0:
            self.stats['success_rate'] = self.stats['total_sortings'] / total_tasks
    
    def _trigger_callbacks(self, event_type: str, data: Any):
        """触发回调函数"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"回调函数执行失败: {e}")
    
    # 公共接口方法
    
    def load_detection_model(self, model_path: str) -> bool:
        """加载检测模型"""
        try:
            if self.detector is None:
                self.detector = GarbageDetector()
            
            self.detector.load_model(model_path)
            self.logger.info(f"检测模型加载成功: {model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载检测模型失败: {e}")
            return False
    
    def set_auto_mode(self, enabled: bool):
        """设置自动模式"""
        self.auto_mode = enabled
        self.logger.info(f"自动模式: {'开启' if enabled else '关闭'}")
    
    def manual_detect(self) -> Optional[Dict]:
        """手动检测"""
        if not self.camera or not self.detector:
            return None
        
        frame = self.camera.get_frame()
        if frame is None:
            return None
        
        return self.detector.detect(frame)
    
    def manual_sort(self, category: str, pickup_position: str = "position_2") -> bool:
        """手动分拣"""
        if not self.robot_arm or not self.robot_arm.is_connected():
            return False
        
        task = SortingTask(
            id=f"manual_{int(time.time() * 1000)}",
            detections=[],
            timestamp=time.time(),
            pickup_position=pickup_position,
            target_category=category
        )
        
        return self._execute_sorting(task)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'state': self.state.value,
            'is_running': self.is_running,
            'auto_mode': self.auto_mode,
            'detector_ready': self.detector is not None and self.detector.model is not None,
            'camera_connected': self.camera is not None and self.camera.is_connected(),
            'robot_arm_connected': self.robot_arm is not None and self.robot_arm.is_connected(),
            'pending_detection_tasks': len(self.detection_tasks),
            'pending_sorting_tasks': len(self.sorting_tasks),
            'stats': self.stats.copy()
        }
    
    def add_callback(self, event_type: str, callback: Callable):
        """添加回调函数"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def emergency_stop(self):
        """紧急停止"""
        self.logger.warning("执行紧急停止")
        
        self.auto_mode = False
        
        # 清空任务队列
        with self.task_lock:
            self.detection_tasks.clear()
            self.sorting_tasks.clear()
        
        # 停止机械臂
        if self.robot_arm:
            self.robot_arm.emergency_stop()
        
        self._set_state(SystemState.IDLE) 