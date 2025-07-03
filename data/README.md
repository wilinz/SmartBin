# 数据集目录

本目录包含SmartBin智能垃圾分拣系统的原始数据集。

## 目录结构

```
data/
├── banana/          # 香蕉皮数据
├── beverages/       # 饮料瓶数据
├── cardboard_box/   # 纸盒数据
├── chips/           # 薯片袋数据
├── fish_bones/      # 鱼骨数据
├── instant_noodles/ # 泡面盒数据
├── milk_box_type1/  # 牛奶盒类型1数据
├── milk_box_type2/  # 牛奶盒类型2数据
├── plastic/         # 塑料数据
└── README.md        # 本说明文件
```

## 数据格式

每个类别目录包含：
- `*.jpg` - 原始图像文件
- `*.xml` - 对应的标注文件(Pascal VOC格式)

## 使用说明

1. 将原始数据放置在对应的类别目录中
2. 运行 `scripts/prepare_data.py` 进行数据预处理
3. 处理后的数据会存储在 `datasets/` 目录中

## 注意事项

- 原始数据文件被 `.gitignore` 忽略，只跟踪目录结构
- 每个目录都有 `.gitkeep` 文件来保持目录结构
- 请确保数据文件命名规范一致

## 数据集统计

- 支持9种垃圾类别
- 每个类别约50张图像
- 总计约450张带标注的图像 