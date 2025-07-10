# 数据增强使用指南

## 🎯 概述

SmartBin 垃圾分拣系统集成了先进的数据增强技术，能够显著提升模型的鲁棒性和泛化能力。通过对原始数据集应用多种变换，可以生成更多样化的训练数据，提高模型在不同环境下的性能。

## 🚀 快速开始

### 1. 标准数据增强

```bash
# 运行标准数据增强
python scripts/prepare_data_with_augmentation.py

# 或者使用默认配置
python scripts/prepare_data_with_augmentation.py --mode normal
```

### 2. 轻量级数据增强（适合测试）

```bash
# 运行轻量级数据增强
python scripts/prepare_data_with_augmentation.py --mode light
```

### 3. 重度数据增强（适合数据稀少的情况）

```bash
# 运行重度数据增强
python scripts/prepare_data_with_augmentation.py --mode heavy
```

### 4. 禁用数据增强

```bash
# 仅进行数据格式转换，不进行增强
python scripts/prepare_data_with_augmentation.py --no-augmentation
```

## 📊 支持的增强技术

### 1. 几何变换
- **旋转 (Rotation)**: 随机旋转图像，提高模型对物体方向的鲁棒性
- **平移 (Translation)**: 随机平移图像，模拟相机位置变化
- **缩放 (Scaling)**: 随机缩放图像，适应不同距离的物体
- **翻转 (Flipping)**: 水平/垂直翻转，增加视角多样性

### 2. 颜色变换
- **亮度调节 (Brightness)**: 模拟不同光照条件
- **对比度调节 (Contrast)**: 增强图像细节对比
- **颜色增强 (Color Enhancement)**: 调整饱和度和色调
- **伽马校正 (Gamma Correction)**: 调整图像亮度曲线

### 3. 噪声和滤波
- **噪声添加 (Noise)**: 添加高斯噪声，模拟真实拍摄条件
- **模糊 (Blur)**: 添加适度模糊，提高对图像质量的容忍度
- **锐化 (Sharpen)**: 增强图像边缘，提高细节清晰度

## ⚙️ 配置参数说明

### 标准配置示例

```python
augmentation_config = {
    'augmentation_factor': 5,  # 每张原图生成5张增强图
    'rotation': {
        'enabled': True,
        'max_angle': 25,        # 最大旋转角度
        'probability': 0.8      # 应用概率
    },
    'brightness': {
        'enabled': True,
        'factor_range': (0.7, 1.3),  # 亮度调节范围
        'probability': 0.7
    },
    # ... 其他配置
}
```

### 参数详解

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `augmentation_factor` | 每张原图生成的增强图数量 | 3-8 |
| `max_angle` | 最大旋转角度（度） | 15-30 |
| `factor_range` | 亮度/对比度调节范围 | (0.7, 1.3) |
| `max_shift` | 最大平移比例 | 0.1-0.2 |
| `scale_range` | 缩放范围 | (0.8, 1.2) |
| `probability` | 应用概率 | 0.3-0.8 |

## 📈 增强效果对比

| 模式 | 增强倍数 | 训练时间 | 模型精度 | 适用场景 |
|------|----------|----------|----------|----------|
| 无增强 | 1x | 最短 | 基准 | 数据充足 |
| 轻量级 | 2-3x | 中等 | +5-10% | 快速验证 |
| 标准 | 5-6x | 较长 | +10-15% | 正式训练 |
| 重度 | 8-10x | 最长 | +15-20% | 数据稀少 |

## 🔧 自定义配置

### 1. 创建自定义配置文件

```python
# custom_augmentation.py
def create_custom_config():
    return {
        'augmentation_factor': 6,
        'rotation': {
            'enabled': True,
            'max_angle': 20,
            'probability': 0.6
        },
        'brightness': {
            'enabled': True,
            'factor_range': (0.8, 1.2),
            'probability': 0.5
        },
        # 添加更多自定义设置...
    }
```

### 2. 使用自定义配置

```python
from src.data_processing.preprocessor import DataPreprocessor
from custom_augmentation import create_custom_config

# 创建预处理器
preprocessor = DataPreprocessor(
    enable_augmentation=True,
    augmentation_config=create_custom_config()
)

# 运行处理
final_dataset_dir = preprocessor.process_data("data", "datasets")
```

## 📋 最佳实践

### 1. 垃圾分类专用建议

- **启用旋转**: 垃圾物体可能以任意角度出现
- **启用亮度调节**: 适应不同光照环境
- **启用噪声**: 模拟真实拍摄条件
- **谨慎使用垂直翻转**: 某些垃圾有明确的上下方向

### 2. 性能优化建议

- **开发阶段**: 使用轻量级配置快速验证
- **正式训练**: 使用标准配置平衡效果和效率
- **数据不足**: 使用重度配置最大化数据利用

### 3. 质量控制

- **检查增强结果**: 确保标注框正确变换
- **验证数据质量**: 避免过度扭曲影响识别
- **监控训练过程**: 及时调整配置参数

## 🛠️ 故障排除

### 常见问题

1. **内存不足**
   - 降低 `augmentation_factor`
   - 分批处理数据
   - 增加系统内存

2. **处理速度慢**
   - 使用轻量级配置
   - 减少启用的增强技术
   - 并行处理优化

3. **标注框错误**
   - 检查原始标注质量
   - 调整变换参数范围
   - 验证坐标变换逻辑

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 保存中间结果
augmentor.save_config("debug_config.json")

# 可视化增强结果
# (添加可视化代码...)
```

## 📊 性能监控

### 训练过程监控

```python
# 记录数据集统计信息
def log_dataset_stats(dataset_dir):
    analysis = preprocessor.analyze_dataset(dataset_dir)
    print(f"总图像数: {analysis['total_images']}")
    print(f"增强倍数: {analysis['total_images']/original_count:.1f}x")
```

### 模型性能评估

- 比较增强前后的验证精度
- 监控过拟合程度
- 评估推理速度影响

## 🎯 下一步

1. **运行数据增强**: 选择合适的配置模式
2. **检查结果**: 验证生成的数据集质量
3. **训练模型**: 使用增强数据集训练模型
4. **优化配置**: 根据训练结果调整参数
5. **部署测试**: 在实际环境中验证效果

## 📚 相关文档

- [模型训练指南](./model_training_guide.md)
- [系统配置说明](./system_configuration.md)
- [性能优化技巧](./performance_optimization.md)

---

*本指南持续更新，如有问题请参考项目文档或提交Issue。* 