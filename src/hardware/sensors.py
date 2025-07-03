#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟传感器控制模块
提供各种传感器的虚拟接口，用于演示和测试
"""

import time
import random
import logging
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# 设置日志记录器
logger = logging.getLogger(__name__)


class SensorType(Enum):
    """传感器类型枚举"""
    PROXIMITY = "proximity"      # 接近传感器
    WEIGHT = "weight"           # 重量传感器
    TEMPERATURE = "temperature"  # 温度传感器
    HUMIDITY = "humidity"       # 湿度传感器
    LIGHT = "light"            # 光照传感器
    PRESSURE = "pressure"      # 压力传感器


@dataclass
class SensorReading:
    """传感器读数"""
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: float
    valid: bool = True
    
    def __str__(self):
        return f"{self.sensor_type.value}: {self.value:.2f} {self.unit}"


class VirtualSensorController:
    """虚拟传感器控制器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化虚拟传感器控制器"""
        self.config = config or {}
        self.is_running = False
        self.sensors = {}
        self.readings = {}
        self.history = {}
        self.thread = None
        self._lock = threading.Lock()
        
        # 初始化传感器
        self._initialize_sensors()
        
        logger.info("虚拟传感器控制器初始化完成")
    
    def _initialize_sensors(self):
        """初始化传感器"""
        # 接近传感器 (垃圾检测位置)
        self.sensors[SensorType.PROXIMITY] = {
            'enabled': True,
            'range': (0, 100),  # cm
            'accuracy': 0.1,
            'description': '检测垃圾是否到达拾取位置'
        }
        
        # 重量传感器 (垃圾重量)
        self.sensors[SensorType.WEIGHT] = {
            'enabled': True,
            'range': (0, 1000),  # g
            'accuracy': 1.0,
            'description': '测量垃圾重量'
        }
        
        # 温度传感器 (环境温度)
        self.sensors[SensorType.TEMPERATURE] = {
            'enabled': True,
            'range': (15, 35),  # °C
            'accuracy': 0.1,
            'description': '环境温度监测'
        }
        
        # 湿度传感器 (环境湿度)
        self.sensors[SensorType.HUMIDITY] = {
            'enabled': True,
            'range': (30, 80),  # %
            'accuracy': 1.0,
            'description': '环境湿度监测'
        }
        
        # 光照传感器 (光照强度)
        self.sensors[SensorType.LIGHT] = {
            'enabled': True,
            'range': (100, 1000),  # lux
            'accuracy': 10,
            'description': '光照强度监测'
        }
        
        # 压力传感器 (系统压力)
        self.sensors[SensorType.PRESSURE] = {
            'enabled': True,
            'range': (95, 105),  # kPa
            'accuracy': 0.1,
            'description': '系统气压监测'
        }
        
        # 初始化历史记录
        for sensor_type in self.sensors:
            self.history[sensor_type] = []
    
    def start_monitoring(self) -> bool:
        """开始传感器监测"""
        try:
            if self.is_running:
                logger.warning("传感器监测已在运行")
                return True
            
            self.is_running = True
            self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.thread.start()
            
            logger.info("传感器监测已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动传感器监测失败: {e}")
            return False
    
    def stop_monitoring(self):
        """停止传感器监测"""
        try:
            self.is_running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
            
            logger.info("传感器监测已停止")
            
        except Exception as e:
            logger.error(f"停止传感器监测失败: {e}")
    
    def _monitoring_loop(self):
        """传感器监测循环"""
        while self.is_running:
            try:
                current_time = time.time()
                
                with self._lock:
                    for sensor_type, config in self.sensors.items():
                        if config['enabled']:
                            # 生成虚拟读数
                            reading = self._generate_reading(sensor_type, current_time)
                            self.readings[sensor_type] = reading
                            
                            # 添加到历史记录
                            self.history[sensor_type].append(reading)
                            
                            # 保持历史记录大小
                            if len(self.history[sensor_type]) > 100:
                                self.history[sensor_type] = self.history[sensor_type][-100:]
                
                time.sleep(1.0)  # 1秒更新一次
                
            except Exception as e:
                logger.error(f"传感器监测循环错误: {e}")
                time.sleep(1.0)
    
    def _generate_reading(self, sensor_type: SensorType, timestamp: float) -> SensorReading:
        """生成虚拟传感器读数"""
        config = self.sensors[sensor_type]
        min_val, max_val = config['range']
        accuracy = config['accuracy']
        
        # 生成基础值（在范围内随机）
        if sensor_type == SensorType.PROXIMITY:
            # 接近传感器：模拟垃圾检测
            base_value = random.choice([5, 95])  # 要么很近(有垃圾)，要么很远(无垃圾)
            if random.random() < 0.1:  # 10%概率切换状态
                base_value = 100 - base_value
        else:
            # 其他传感器：在范围内随机波动
            center = (min_val + max_val) / 2
            variation = (max_val - min_val) * 0.1  # 10%的变化范围
            base_value = center + random.uniform(-variation, variation)
            base_value = max(min_val, min(max_val, base_value))
        
        # 添加噪音
        noise = random.uniform(-accuracy, accuracy)
        value = base_value + noise
        value = max(min_val, min(max_val, value))
        
        # 确定单位
        units = {
            SensorType.PROXIMITY: "cm",
            SensorType.WEIGHT: "g",
            SensorType.TEMPERATURE: "°C",
            SensorType.HUMIDITY: "%",
            SensorType.LIGHT: "lux",
            SensorType.PRESSURE: "kPa"
        }
        
        return SensorReading(
            sensor_type=sensor_type,
            value=round(value, 2),
            unit=units[sensor_type],
            timestamp=timestamp,
            valid=True
        )
    
    def get_reading(self, sensor_type: SensorType) -> Optional[SensorReading]:
        """获取指定传感器的当前读数"""
        with self._lock:
            return self.readings.get(sensor_type)
    
    def get_all_readings(self) -> Dict[SensorType, SensorReading]:
        """获取所有传感器的当前读数"""
        with self._lock:
            return self.readings.copy()
    
    def get_history(self, sensor_type: SensorType, limit: int = 10) -> List[SensorReading]:
        """获取传感器历史数据"""
        with self._lock:
            history = self.history.get(sensor_type, [])
            return history[-limit:] if limit > 0 else history
    
    def is_garbage_detected(self) -> bool:
        """检测是否有垃圾（基于接近传感器）"""
        reading = self.get_reading(SensorType.PROXIMITY)
        if reading and reading.valid:
            return reading.value < 20  # 距离小于20cm认为有垃圾
        return False
    
    def get_garbage_weight(self) -> float:
        """获取垃圾重量"""
        reading = self.get_reading(SensorType.WEIGHT)
        if reading and reading.valid:
            # 如果检测到垃圾，返回模拟重量
            if self.is_garbage_detected():
                return max(reading.value, 10)  # 至少10g
            else:
                return 0.0
        return 0.0
    
    def get_environmental_data(self) -> Dict[str, float]:
        """获取环境数据"""
        temp_reading = self.get_reading(SensorType.TEMPERATURE)
        humidity_reading = self.get_reading(SensorType.HUMIDITY)
        light_reading = self.get_reading(SensorType.LIGHT)
        pressure_reading = self.get_reading(SensorType.PRESSURE)
        
        return {
            'temperature': temp_reading.value if temp_reading else 25.0,
            'humidity': humidity_reading.value if humidity_reading else 50.0,
            'light': light_reading.value if light_reading else 500.0,
            'pressure': pressure_reading.value if pressure_reading else 100.0
        }
    
    def enable_sensor(self, sensor_type: SensorType) -> bool:
        """启用传感器"""
        try:
            if sensor_type in self.sensors:
                self.sensors[sensor_type]['enabled'] = True
                logger.info(f"传感器 {sensor_type.value} 已启用")
                return True
            return False
        except Exception as e:
            logger.error(f"启用传感器失败: {e}")
            return False
    
    def disable_sensor(self, sensor_type: SensorType) -> bool:
        """禁用传感器"""
        try:
            if sensor_type in self.sensors:
                self.sensors[sensor_type]['enabled'] = False
                logger.info(f"传感器 {sensor_type.value} 已禁用")
                return True
            return False
        except Exception as e:
            logger.error(f"禁用传感器失败: {e}")
            return False
    
    def get_sensor_status(self) -> Dict:
        """获取传感器状态"""
        status = {}
        for sensor_type, config in self.sensors.items():
            reading = self.get_reading(sensor_type)
            status[sensor_type.value] = {
                'enabled': config['enabled'],
                'description': config['description'],
                'current_value': reading.value if reading else None,
                'unit': reading.unit if reading else None,
                'last_update': reading.timestamp if reading else None,
                'valid': reading.valid if reading else False
            }
        return status
    
    def reset_history(self):
        """清除历史数据"""
        with self._lock:
            for sensor_type in self.history:
                self.history[sensor_type].clear()
        logger.info("传感器历史数据已清除")
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'is_running') and self.is_running:
            self.stop_monitoring()


# 创建全局实例
sensor_controller = VirtualSensorController()


class SensorController:
    """传感器控制器（兼容性别名）"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.controller = VirtualSensorController(config)
    
    def __getattr__(self, name):
        """将所有属性和方法委托给虚拟控制器"""
        return getattr(self.controller, name)


# 导出接口
__all__ = [
    'VirtualSensorController',
    'SensorController',
    'sensor_controller',
    'SensorType',
    'SensorReading'
] 