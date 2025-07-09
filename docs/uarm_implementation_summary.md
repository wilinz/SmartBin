# uArm 机械臂实现总结

## 概述

根据您的要求，我们参考 `uarm_demo` 目录实现了 uArm 机械臂功能，并删除了其他机械臂实现，现在系统只支持 uArm 机械臂和虚拟机械臂。

## 完成的工作

### 1. 新增 uArm 机械臂实现

**文件**: `src/hardware/robot_arm_uarm.py`

- ✅ 基于 `uarm_demo/arm1.py` 的实现
- ✅ 继承 `RobotArmInterface` 接口
- ✅ 自动端口检测（Windows/Linux/macOS）
- ✅ 完整的机械臂控制功能：
  - 连接/断开管理
  - 归位、移动、抓取、释放
  - 关节角度控制
  - 紧急停止
  - 状态监控
- ✅ 专门的垃圾分拣功能
- ✅ 9种垃圾类型的预定义位置

### 2. 删除不需要的实现

**删除的文件**: `src/hardware/robot_arm_example.py`

- ✅ 移除了 UR、KUKA 等其他机械臂实现
- ✅ 简化了代码结构

### 3. 更新接口和控制器

**更新的文件**:
- `src/hardware/robot_arm_interface.py`
- `src/hardware/robot_arm.py`

**更新内容**:
- ✅ 工厂函数只支持 `virtual` 和 `uarm` 两种类型
- ✅ 更新了支持的机械臂类型列表
- ✅ 更新了机械臂类型信息
- ✅ 移除了对其他机械臂的引用

### 4. 更新配置文件

**更新的文件**: `config/hardware_config.yaml`

**更新内容**:
- ✅ 添加了 uArm 机械臂专用配置
- ✅ 更新了位置配置以匹配 uArm 工作空间
- ✅ 更新了运动参数以匹配 uArm 规格
- ✅ 配置了9种垃圾类型的投放位置

### 5. 创建测试脚本

**新增文件**: `scripts/test_uarm.py`

**功能**:
- ✅ uArm 机械臂基本功能测试
- ✅ 垃圾分拣功能测试
- ✅ 虚拟机械臂功能测试
- ✅ 交互式测试菜单

## 支持的机械臂类型

现在系统只支持以下两种机械臂：

### 1. 虚拟机械臂 (`virtual`)
- 用于测试和演示
- 仿真垃圾分拣过程
- 提供统计信息和操作历史

### 2. uArm 机械臂 (`uarm`)
- 基于 `uarm_demo` 实现
- 支持 uArm Swift/Swift Pro
- 真实硬件控制
- 垃圾分拣功能

## 垃圾分拣支持

系统支持以下 9 种垃圾类型的自动分拣：

| 垃圾类型 | 中文名称 | 分类 | 投放位置 |
|----------|----------|------|----------|
| `banana` | 香蕉皮 | 厨余垃圾 | (200, 50, 50) |
| `beverages` | 饮料瓶 | 可回收垃圾 | (200, -50, 50) |
| `cardboard_box` | 纸盒 | 可回收垃圾 | (150, 50, 50) |
| `chips` | 薯片袋 | 其他垃圾 | (150, -50, 50) |
| `fish_bones` | 鱼骨 | 厨余垃圾 | (250, 50, 50) |
| `instant_noodles` | 泡面盒 | 其他垃圾 | (250, -50, 50) |
| `milk_box_type1` | 牛奶盒1 | 可回收垃圾 | (180, 30, 50) |
| `milk_box_type2` | 牛奶盒2 | 可回收垃圾 | (180, -30, 50) |
| `plastic` | 塑料 | 可回收垃圾 | (220, 0, 50) |

## 使用方法

### 1. 基本使用

```python
from src.hardware.robot_arm import RobotArmController

# 创建 uArm 机械臂控制器
config = {
    'arm_type': 'uarm',
    'port': None,  # 自动检测端口
    'baudrate': 115200,
    'speed_factor': 100
}

arm = RobotArmController(config)

# 连接机械臂
if arm.connect():
    print("连接成功！")
    
    # 归位
    arm.home()
    
    # 移动到指定位置
    from src.hardware.robot_arm_interface import Position
    arm.move_to_position(Position(x=200, y=0, z=100))
    
    # 抓取物体
    arm.grab_object()
    
    # 垃圾分拣
    arm.sort_garbage('banana')
    
    # 断开连接
    arm.disconnect()
```

### 2. 使用测试脚本

```bash
# 运行测试脚本
python scripts/test_uarm.py

# 选择测试模式
# 1. 测试 uArm 机械臂基本功能
# 2. 测试 uArm 机械臂垃圾分拣功能
# 3. 测试虚拟机械臂功能
# 4. 运行所有测试
```

## 配置说明

### uArm 机械臂配置参数

```yaml
robot_arm:
  type: "uarm"
  uarm:
    port: null              # 串口端口，null表示自动检测
    baudrate: 115200        # 波特率
    speed_factor: 100       # 速度系数 (1-100)
    timeout: 1.0            # 超时时间
```

### 运动参数

```yaml
motion:
  speed: 50                 # 运动速度 (mm/s)
  acceleration: 100         # 加速度 (mm/s²)
  precision: 1              # 定位精度 (mm)
  max_reach: 350            # 最大工作半径 (mm)
  max_payload: 500          # 最大负载 (g)
  degrees_of_freedom: 3     # 自由度
```

## 依赖要求

1. **uarm_demo 库**: 需要 `uarm_demo` 目录中的 uArm 库
2. **串口库**: `pyserial` 用于串口通信
3. **系统权限**: 需要串口访问权限

## 注意事项

1. **端口检测**: 
   - Windows: 自动检测 COM 端口
   - Linux/macOS: 优先使用 `/dev/serial/by-id/`，备用常见端口

2. **安全性**: 
   - 包含紧急停止功能
   - 移动前进行连接状态检查
   - 异常处理和错误恢复

3. **兼容性**: 
   - 保持与原有接口的完全兼容
   - 支持向后兼容的属性访问

4. **扩展性**: 
   - 可以轻松添加新的垃圾类型
   - 支持自定义投放位置
   - 模块化设计便于维护

## 测试建议

1. 首先运行虚拟机械臂测试，确保软件架构正常
2. 确保 uArm 机械臂正确连接并有足够的操作空间
3. 运行基本功能测试，检查连接和移动功能
4. 运行垃圾分拣测试，验证完整的分拣流程

## 问题排查

### 连接失败
- 检查 uArm 机械臂是否正确连接
- 检查串口权限 (Linux: `sudo chmod 666 /dev/ttyUSB0`)
- 确保 `uarm_demo` 库可用

### 移动失败
- 检查目标位置是否在工作空间内
- 确保机械臂已正确归位
- 检查是否有物理障碍

### 分拣失败
- 确保垃圾类型在支持列表中
- 检查投放位置是否可达
- 验证抓取功能是否正常 