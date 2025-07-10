# uArm 串口通信实现说明

## 概述

基于 `uarm_demo/uarm_demo.py` 的经过测试的可运行代码，完全重新实现了 SmartBin 项目的机械臂控制系统。新实现使用串口通信和 G-code 命令控制，具有更高的可靠性和更好的兼容性。

## 核心变更

### 1. 通信方式变更

| 方面 | 原实现 | 新实现 |
|------|--------|--------|
| 通信协议 | SwiftAPI | 串口通信 |
| 控制命令 | API方法调用 | G-code命令 |
| 依赖库 | uarm python库 | 标准串口库 |
| 连接验证 | API状态查询 | M114位置查询 |

### 2. 架构优化

#### 原架构
```
SmartBin System
    ↓
SwiftAPI (uarm库)
    ↓
uArm 机械臂
```

#### 新架构
```
SmartBin System
    ↓
串口通信 + G-code
    ↓
uArm 机械臂
```

## 主要组件

### 1. UarmRobotArm 类 (串口版本)

```python
class UarmRobotArm(RobotArmInterface):
    """
    基于串口通信的 uArm 机械臂实现
    """
    
    def __init__(self, config: Optional[Dict] = None):
        # 配置串口参数
        self.port = self.config.get('port', None)
        self.baudrate = self.config.get('baudrate', 115200)
        self.timeout = self.config.get('timeout', 1)
        
        # 创建串口连接
        self.arm = None  # serial.Serial 实例
```

### 2. 核心方法实现

#### 连接管理
```python
def connect(self) -> bool:
    """使用串口连接机械臂"""
    self.arm = serial.Serial(
        port=port,
        baudrate=self.baudrate,
        timeout=self.timeout,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE
    )
    
    # 测试连接
    self.arm.write(b"M114\r\n")  # 获取位置命令
```

#### G-code命令发送
```python
def send_command(self, command: str) -> bool:
    """发送G-code指令"""
    command_bytes = f"{command}\r\n".encode()
    self.arm.write(command_bytes)
```

#### 位置控制
```python
def move_to_position(self, position: Position, speed: Optional[float] = None) -> bool:
    """使用G-code控制移动"""
    speed_value = int(speed) if speed else 1000
    command = f"G0 X{position.x} Y{position.y} Z{position.z} F{speed_value}"
    return self.send_command(command)
```

#### 机械爪控制
```python
def grab_object(self, parameters: Optional[GrabParameters] = None) -> bool:
    """使用G-code控制抓取"""
    self.send_command("M2232 V1")  # 1为关闭（抓取）

def release_object(self) -> bool:
    """使用G-code控制释放"""
    self.send_command("M2232 V0")  # 0为打开（释放）
```

### 3. 坐标转换系统

#### CoordinateTransform 类
```python
class CoordinateTransform:
    """
    图像坐标到机械臂坐标的转换
    使用单应性矩阵实现精确转换
    """
    
    def __init__(self, camera_coordinates=None, robot_coordinates=None):
        # 使用 uarm_demo.py 中的标定点
        self.camera_points = np.array([
            [0, 0],     [640, 0],
            [640, 480], [0, 480]
        ], dtype=np.float32)
        
        self.robot_points = np.array([
            [91.3, -99.5],   [88.4, 35.5],
            [205.7, 40.9],   [211.5, -120.2]
        ], dtype=np.float32)
        
        # 计算单应性矩阵
        self.H, _ = cv2.findHomography(self.camera_points, self.robot_points)
```

### 4. 完整的拾取流程

```python
def pick_object(self, x: float, y: float, class_id: int) -> bool:
    """
    完整的拾取和分类放置流程
    基于 uarm_demo.py 的实现
    """
    # 1. 移动到物体上方
    self.move_to_position(Position(x=x, y=y, z=50))
    
    # 2. 下降到物体位置
    self.move_to_position(Position(x=x, y=y, z=self.polar_height))
    
    # 3. 抓取物体
    self.grab_object()
    
    # 4. 抬起物体
    self.move_to_position(Position(x=x, y=y, z=50))
    
    # 5. 移动到分类区域
    target_x, target_y = self.get_classification_position(class_id)
    self.move_to_position(Position(x=target_x, y=target_y, z=50))
    
    # 6. 释放物体
    self.release_object()
    
    # 7. 返回初始位置
    self.home()
```

## G-code 命令参考

### 移动控制
| 命令 | 说明 | 示例 |
|------|------|------|
| G0 | 快速移动 | `G0 X150 Y0 Z90 F1000` |
| G1 | 线性移动 | `G1 X100 Y50 Z30 F500` |

### 工具控制
| 命令 | 说明 | 示例 |
|------|------|------|
| M2231 | 手腕角度控制 | `M2231 V0` (设置角度为0) |
| M2232 | 机械爪控制 | `M2232 V1` (关闭), `M2232 V0` (打开) |

### 状态查询
| 命令 | 说明 | 示例 |
|------|------|------|
| M114 | 获取当前位置 | `M114` |

## 垃圾分类配置

### 分类位置 (基于 uarm_demo.py)

```python
garbage_positions = {
    # 厨余垃圾
    'banana': {'x': 20.6, 'y': 127.1, 'z': 50},
    'fish_bones': {'x': 20.6, 'y': 127.1, 'z': 50},
    
    # 可回收垃圾
    'beverages': {'x': 99.5, 'y': 121.7, 'z': 50},
    'cardboard_box': {'x': 99.5, 'y': 121.7, 'z': 50},
    'milk_box_type1': {'x': 99.5, 'y': 121.7, 'z': 50},
    'milk_box_type2': {'x': 99.5, 'y': 121.7, 'z': 50},
    'plastic': {'x': 99.5, 'y': 121.7, 'z': 50},
    
    # 其他垃圾
    'chips': {'x': 189.6, 'y': 142.4, 'z': 50},
    'instant_noodles': {'x': 189.6, 'y': 142.4, 'z': 50},
}
```

### 类别映射

```python
def get_classification_position(self, class_id: int) -> tuple:
    """根据类别ID返回分类位置"""
    if class_id in [0, 4]:  # banana, fish_bones - 厨余垃圾
        return (20.6, 127.1)
    elif class_id in [1, 2, 6, 7, 8]:  # 可回收垃圾
        return (99.5, 121.7)
    else:  # 其他垃圾
        return (189.6, 142.4)
```

## 使用方法

### 1. 基本使用

```python
from src.hardware.robot_arm_uarm import UarmRobotArm
from src.hardware.coordinate_transform import CoordinateTransform
from src.hardware.robot_arm_interface import Position

# 创建机械臂实例
config = {
    'baudrate': 115200,
    'timeout': 1
}
arm = UarmRobotArm(config)

# 创建坐标转换器
transformer = CoordinateTransform()

# 连接机械臂
if arm.connect():
    # 复位
    arm.home()
    
    # 图像坐标转换为机械臂坐标
    image_x, image_y = 320, 240  # 图像中心
    robot_x, robot_y = transformer.convert_coordinate(image_x, image_y)
    
    # 移动到转换后的位置
    arm.move_to_position(Position(x=robot_x, y=robot_y, z=50))
    
    # 执行完整的拾取流程
    arm.pick_object(robot_x, robot_y, class_id=0)
    
    # 断开连接
    arm.disconnect()
```

### 2. 运行测试

```bash
# 测试串口通信
python scripts/test_uarm_serial.py

# 测试坐标转换
python src/hardware/coordinate_transform.py
```

### 3. 状态监控

```python
# 获取状态
status = arm.get_status()
print(f"连接状态: {status['connected']}")
print(f"通信类型: {status['communication_type']}")
print(f"端口: {status['port']}")
print(f"波特率: {status['baudrate']}")
```

## 优势对比

### 相比原 SwiftAPI 实现

| 优势 | 说明 |
|------|------|
| **可靠性** | 直接串口通信，减少中间层 |
| **兼容性** | 不依赖特定的 Python 库版本 |
| **透明度** | G-code 命令清晰可见 |
| **调试性** | 可以直接发送命令进行调试 |
| **扩展性** | 易于添加新的 G-code 功能 |

### 相比原 arm1.py 实现

| 优势 | 说明 |
|------|------|
| **系统集成** | 完整的接口兼容性 |
| **坐标转换** | 精确的图像到机械臂坐标转换 |
| **分类逻辑** | 完整的垃圾分类系统 |
| **错误处理** | 完善的异常处理机制 |
| **状态管理** | 详细的状态跟踪 |

## 注意事项

### 1. 硬件要求
- uArm 机械臂正确连接到电脑
- USB 驱动正确安装
- 串口权限配置（Linux/macOS）

### 2. 软件依赖
```python
# 基本依赖
import serial          # 串口通信
import numpy as np     # 数值计算
import cv2            # 图像处理（坐标转换）
```

### 3. 配置参数
```python
config = {
    'port': None,        # 自动检测或指定端口
    'baudrate': 115200,  # 波特率
    'timeout': 1         # 超时时间
}
```

### 4. 安全注意事项
- 确保机械臂周围无障碍物
- 验证坐标转换的准确性
- 测试工作空间边界
- 定期检查硬件连接

## 故障排除

### 1. 连接问题
```bash
# 检查串口设备
ls /dev/tty* | grep -E "(USB|ACM)"

# 检查权限 (Linux)
sudo chmod 666 /dev/ttyUSB0
```

### 2. 坐标转换问题
```python
# 验证转换
transformer = CoordinateTransform()
transformer.validate_transform()

# 检查工作空间
safe_coord = transformer.get_safe_coordinate(x, y)
```

### 3. G-code 命令问题
```python
# 直接发送测试命令
arm.send_command("M114")  # 获取位置
arm.send_command("G0 X150 Y0 Z90 F1000")  # 移动测试
```

## 技术支持

如果遇到问题：

1. 确认 `uarm_demo/uarm_demo.py` 可以正常运行
2. 检查串口连接和权限
3. 验证坐标转换参数
4. 查看详细的错误日志
5. 参考测试脚本进行排查

## 更新日志

- **v2.0** (当前版本)
  - 完全基于 `uarm_demo.py` 重新实现
  - 使用串口通信替代 SwiftAPI
  - 添加坐标转换功能
  - 实现完整的垃圾分拣流程
  - 提供详细的测试和文档

- **v1.0** (原版本)
  - 基于 SwiftAPI 实现
  - 基本的机械臂控制功能
  - 简单的预设位置分拣 