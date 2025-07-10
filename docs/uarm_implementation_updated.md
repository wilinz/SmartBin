# uArm 机械臂实现更新说明

## 概述

基于 `uarm_demo/arm1.py` 的可运行demo，重新实现了 uArm 机械臂的控制代码。这个实现确保了与经过测试的demo代码的兼容性和稳定性。

## 主要改进

### 1. 基于可运行的Demo实现

- **参考文件**: `uarm_demo/arm1.py`
- **优势**: 该demo已经过测试，确认可以正常运行
- **实现**: 直接采用demo中的端口检测、连接、控制逻辑

### 2. 端口检测优化

```python
def _check_port(self, port: Optional[str] = None) -> Optional[str]:
    """检测并返回 uArm 机械臂端口（基于 arm1.py 的实现）"""
    # Windows 系统端口检测
    if platform.system() == 'Windows':
        plist = list(serial.tools.list_ports.comports())
        if len(plist) <= 0:
            print("❌ 未找到串口设备!")
        else:
            plist_0 = list(plist[0])
            detected_port = plist_0[0]
            print(f'✅ 当前设备: {detected_port}')
    else:
        # Linux/macOS 系统端口检测
        ret = os.popen("ls /dev/serial/by-id").read()
        if ret.strip():
            detected_port = "/dev/serial/by-id/" + ret.split('\n')[0].split('/')[-1]
            print(f'✅ 当前设备: {detected_port}')
```

### 3. 连接验证增强

```python
def connect(self) -> bool:
    """连接 uArm 机械臂（基于 arm1.py 的实现）"""
    # 创建 SwiftAPI 实例
    self.arm = SwiftAPI(port=port, baudrate=self.baudrate)
    
    # 验证连接 - 尝试获取设备信息
    device_info = self.arm.get_device_info()
    power_status = self.arm.get_power_status()
    
    print(f"✅ 设备信息: {device_info}")
    print(f"✅ 电源状态: {power_status}")
```

### 4. 控制方法优化

#### 抓取控制
```python
def grab_object(self, parameters: Optional[GrabParameters] = None) -> bool:
    """抓取物体（基于 arm1.py 的实现）"""
    # 控制吸盘打开
    self.arm.set_pump(on=True)
    
    # 增加等待时间，确保抓取稳定
    time.sleep(3)
    
    # 检查抓取状态
    pump_status = self.arm.get_pump_status()
    print(f"吸盘状态: {pump_status}")
```

#### 位置控制
```python
def move_to_position(self, position: Position, speed: Optional[float] = None) -> bool:
    """移动到指定位置（基于 arm1.py 的实现）"""
    # 直接使用 arm1.py 的移动方式
    self.arm.set_position(x=position.x, y=position.y, z=position.z)
    
    # 打印当前位置
    current_pos = self.arm.get_position()
    print(f"✅ 移动完成，当前位置: {current_pos}")
```

## 使用方法

### 1. 基本使用

```python
from src.hardware.robot_arm_uarm import UarmRobotArm
from src.hardware.robot_arm_interface import Position

# 创建机械臂实例
config = {
    'baudrate': 115200,
    'speed_factor': 100
}
arm = UarmRobotArm(config)

# 连接机械臂
if arm.connect():
    print("✅ 连接成功")
    
    # 复位
    arm.home()
    
    # 移动到指定位置
    position = Position(x=200, y=0, z=100)
    arm.move_to_position(position)
    
    # 抓取物体
    arm.grab_object()
    
    # 释放物体
    arm.release_object()
    
    # 断开连接
    arm.disconnect()
```

### 2. 运行测试

```bash
# 运行基本测试
python scripts/test_uarm_updated.py

# 运行详细测试
python scripts/test_uarm_updated.py --detailed
```

### 3. 状态监控

```python
# 获取详细状态信息
status = arm.get_status()
print(f"连接状态: {status['connected']}")
print(f"当前位置: {status['current_position']}")
print(f"吸盘状态: {status['pump_status']}")

# 获取所有传感器信息
if arm.is_connected():
    print(f"电源状态: {arm.arm.get_power_status()}")
    print(f"设备信息: {arm.arm.get_device_info()}")
    print(f"吸盘限位开关: {arm.arm.get_limit_switch()}")
    print(f"电动夹状态: {arm.arm.get_gripper_catch()}")
    print(f"吸盘状态: {arm.arm.get_pump_status()}")
    print(f"模式状态: {arm.arm.get_mode()}")
```

## 垃圾分拣功能

### 预设位置

```python
garbage_positions = {
    'banana': {'x': 200, 'y': 50, 'z': 50},      # 香蕉皮 - 厨余垃圾
    'beverages': {'x': 200, 'y': -50, 'z': 50},  # 饮料瓶 - 可回收垃圾
    'cardboard_box': {'x': 150, 'y': 50, 'z': 50}, # 纸盒 - 可回收垃圾
    'chips': {'x': 150, 'y': -50, 'z': 50},     # 薯片袋 - 其他垃圾
    'fish_bones': {'x': 250, 'y': 50, 'z': 50}, # 鱼骨 - 厨余垃圾
    'instant_noodles': {'x': 250, 'y': -50, 'z': 50}, # 泡面盒 - 其他垃圾
    'milk_box_type1': {'x': 180, 'y': 30, 'z': 50},   # 牛奶盒1 - 可回收垃圾
    'milk_box_type2': {'x': 180, 'y': -30, 'z': 50},  # 牛奶盒2 - 可回收垃圾
    'plastic': {'x': 220, 'y': 0, 'z': 50}      # 塑料 - 可回收垃圾
}
```

### 垃圾分拣

```python
# 分拣指定类型的垃圾
if arm.sort_garbage('banana'):
    print("✅ 香蕉皮分拣完成")
else:
    print("❌ 垃圾分拣失败")
```

## 高级功能

### 1. 直接控制API

```python
# 直接访问 uArm API
if arm.is_connected():
    # 设置手腕角度
    arm.arm.set_wrist(180)
    
    # 控制蜂鸣器
    arm.arm.set_buzzer(frequency=1000)
    
    # 极坐标移动
    arm.arm.set_polar(stretch=200, rotation=90, height=150)
    
    # 关节角度控制
    arm.arm.set_servo_angle(servo_id=0, angle=60)
```

### 2. 错误处理

```python
# 检查错误
if arm.errors:
    print(f"错误列表: {arm.errors}")
    
    # 重置错误
    arm.reset_errors()

# 紧急停止
arm.emergency_stop()
```

## 故障排除

### 1. 连接问题

- 确保 uArm 机械臂已正确连接到电脑
- 检查 USB 驱动是否正确安装
- 确认端口权限（Linux/macOS）

### 2. 导入问题

- 确保 `uarm_demo` 目录存在
- 检查 uArm 库是否正确安装
- 验证 Python 路径配置

### 3. 控制问题

- 检查机械臂电源状态
- 确认机械臂未处于错误状态
- 验证移动范围是否在工作空间内

## 与原demo的对比

| 功能 | arm1.py | 更新后实现 | 说明 |
|------|---------|------------|------|
| 端口检测 | ✅ | ✅ | 完全兼容 |
| 连接验证 | ✅ | ✅ | 增强验证 |
| 基本控制 | ✅ | ✅ | 接口封装 |
| 状态获取 | ✅ | ✅ | 扩展状态 |
| 错误处理 | ❌ | ✅ | 新增功能 |
| 垃圾分拣 | ❌ | ✅ | 新增功能 |

## 注意事项

1. **安全第一**: 使用前确保机械臂周围无障碍物
2. **测试环境**: 建议先在测试环境中运行
3. **定期维护**: 定期检查机械臂状态和连接
4. **备份配置**: 保存重要的配置参数

## 技术支持

如果在使用过程中遇到问题，请：

1. 检查 `uarm_demo/arm1.py` 是否能正常运行
2. 查看错误日志和状态信息
3. 参考测试脚本 `scripts/test_uarm_updated.py`
4. 检查硬件连接和电源状态 