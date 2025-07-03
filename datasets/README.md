# 处理后的数据集目录

本目录包含经过预处理的数据集，用于训练和测试YOLO模型。

## 目录结构

```
datasets/
├── converted/       # 转换后的数据
│   ├── images/      # 所有图像文件
│   └── labels/      # 对应的YOLO格式标注文件
├── yolo_dataset/    # YOLO训练格式数据集
│   ├── train/       # 训练数据
│   │   ├── images/  # 训练图像
│   │   └── labels/  # 训练标注
│   ├── val/         # 验证数据
│   │   ├── images/  # 验证图像
│   │   └── labels/  # 验证标注
│   ├── test/        # 测试数据
│   │   ├── images/  # 测试图像
│   │   └── labels/  # 测试标注
│   └── dataset.yaml # 数据集配置文件
└── README.md        # 本说明文件
```

## 数据格式

### converted/ 目录
- 包含从Pascal VOC格式转换为YOLO格式的所有数据
- 图像文件：`.jpg`
- 标注文件：`.txt` (YOLO格式)

### yolo_dataset/ 目录
- 按训练/验证/测试集分割的数据
- 比例通常为：70% 训练，20% 验证，10% 测试
- 包含 `dataset.yaml` 配置文件

## 生成流程

1. 从 `data/` 目录读取原始数据
2. 运行 `scripts/prepare_data.py` 进行数据转换
3. 自动生成 `converted/` 目录
4. 自动分割数据集生成 `yolo_dataset/` 目录

## 使用说明

### 训练模型
```bash
# 使用 yolo_dataset 进行训练
python scripts/train_yolo.py --data datasets/yolo_dataset/dataset.yaml
```

### 验证模型
```bash
# 使用验证集测试模型性能
python scripts/validate_model.py --data datasets/yolo_dataset/dataset.yaml
```

## 注意事项

- 处理后的数据文件被 `.gitignore` 忽略，只跟踪目录结构
- 每个目录都有 `.gitkeep` 文件来保持目录结构
- 重新生成数据集会覆盖现有文件
- 确保原始数据在 `data/` 目录中正确放置 