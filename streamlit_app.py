#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Streamlit的数据集可视化应用
用于展示和分析dataset-with-label数据集
"""

import streamlit as st
import os
from pathlib import Path
import random
from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# 页面配置
st.set_page_config(
    page_title="数据集可视化工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 类别映射
CATEGORY_MAPPING = {
    "beverages": "饮料",
    "banana": "香蕉", 
    "plastic": "塑料",
    "milk_box_type2": "牛奶盒2",
    "milk_box_type1": "牛奶盒1",
    "instant_noodles": "泡面",
    "fish_bones": "鱼骨头",
    "chips": "薯片",
    "cardboard_box": "纸箱"
}

@st.cache_data
def load_dataset_info(dataset_path="dataset-with-label"):
    """
    加载数据集信息
    """
    dataset_path = Path(dataset_path)
    
    if not dataset_path.exists():
        return None, None
    
    categories_data = {}
    total_images = 0
    
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', 
                       '.JPG', '.JPEG', '.PNG', '.GIF', '.BMP', '.TIFF', '.WEBP'}
    
    for category_dir in dataset_path.iterdir():
        if category_dir.is_dir() and not category_dir.name.startswith('.'):
            # 统计图片数量
            image_files = [f for f in category_dir.iterdir() 
                          if f.is_file() and f.suffix in image_extensions]
            
            count = len(image_files)
            total_images += count
            
            categories_data[category_dir.name] = {
                'count': count,
                'chinese_name': CATEGORY_MAPPING.get(category_dir.name, category_dir.name),
                'files': image_files[:100]  # 最多缓存100个文件路径
            }
    
    return categories_data, total_images

@st.cache_data
def get_sample_images(category_path, num_samples=9):
    """
    获取类别的样本图片
    """
    category_path = Path(category_path)
    
    if not category_path.exists():
        return []
    
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', 
                       '.JPG', '.JPEG', '.PNG', '.GIF', '.BMP', '.TIFF', '.WEBP'}
    
    image_files = [f for f in category_path.iterdir() 
                  if f.is_file() and f.suffix in image_extensions]
    
    # 随机选择样本
    if len(image_files) > num_samples:
        sample_files = random.sample(image_files, num_samples)
    else:
        sample_files = image_files
    
    return sample_files

def display_image_grid(image_files, cols=3, show_details=True):
    """
    以网格形式显示图片，包含详细标注信息
    """
    if not image_files:
        st.warning("没有找到图片文件")
        return
    
    # 创建网格
    for i in range(0, len(image_files), cols):
        col_list = st.columns(cols)
        
        for j, col in enumerate(col_list):
            if i + j < len(image_files):
                image_file = image_files[i + j]
                try:
                    with col:
                        image = Image.open(image_file)
                        original_size = image.size
                        
                        # 调整大小以适应显示
                        image.thumbnail((300, 300))
                        
                        # 显示图片
                        st.image(image, use_container_width=True)
                        
                        # 显示详细标注信息
                        if show_details:
                            st.markdown("**📝 图片标注信息**")
                            
                            # 基本信息
                            file_info = {
                                "文件名": image_file.name,
                                "原始尺寸": f"{original_size[0]} × {original_size[1]}",
                                "文件大小": f"{image_file.stat().st_size / 1024:.1f} KB",
                                "格式": image_file.suffix.upper().replace('.', '')
                            }
                            
                            # 从文件名推断的标注信息
                            category_from_path = image_file.parent.name
                            chinese_name = CATEGORY_MAPPING.get(category_from_path, category_from_path)
                            
                            # 显示标注
                            st.markdown(f"🏷️ **类别**: {chinese_name}")
                            st.markdown(f"📁 **英文类别**: {category_from_path}")
                            
                            # 显示详细信息（可折叠）
                            with st.expander("查看详细信息"):
                                for key, value in file_info.items():
                                    st.write(f"**{key}**: {value}")
                                
                                # 如果是JPG文件，尝试读取EXIF信息
                                try:
                                    if hasattr(image, '_getexif') and image._getexif():
                                        st.write("**EXIF信息**: 存在")
                                    else:
                                        st.write("**EXIF信息**: 无")
                                except:
                                    st.write("**EXIF信息**: 无法读取")
                        
                        st.divider()
                        
                except Exception as e:
                    col.error(f"无法加载图片: {image_file.name}")
                    col.write(f"错误信息: {str(e)}")

def create_distribution_chart(categories_data):
    """
    创建数据分布图表
    """
    if not categories_data:
        return None
    
    # 准备数据
    data = []
    for category, info in categories_data.items():
        data.append({
            'category': category,
            'chinese_name': info['chinese_name'], 
            'count': info['count']
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('count', ascending=False)
    
    # 创建柱状图
    fig = px.bar(
        df, 
        x='chinese_name', 
        y='count',
        title='各类别样本数量分布',
        labels={'chinese_name': '类别', 'count': '样本数量'},
        color='count',
        color_continuous_scale='viridis'
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        showlegend=False
    )
    
    return fig

def create_pie_chart(categories_data):
    """
    创建饼图
    """
    if not categories_data:
        return None
    
    labels = [info['chinese_name'] for info in categories_data.values()]
    values = [info['count'] for info in categories_data.values()]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values,
        hovertemplate='<b>%{label}</b><br>样本数量: %{value}<br>占比: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title_text="数据集类别分布",
        height=500
    )
    
    return fig

def analyze_category_images(category_path):
    """
    分析类别中所有图片的详细信息
    """
    category_path = Path(category_path)
    
    if not category_path.exists():
        return None
    
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', 
                       '.JPG', '.JPEG', '.PNG', '.GIF', '.BMP', '.TIFF', '.WEBP'}
    
    image_files = [f for f in category_path.iterdir() 
                  if f.is_file() and f.suffix in image_extensions]
    
    if not image_files:
        return None
    
    analysis_data = []
    total_size = 0
    formats = {}
    resolutions = {}
    
    for image_file in image_files:
        try:
            with Image.open(image_file) as image:
                width, height = image.size
                file_size = image_file.stat().st_size
                format_type = image.format or image_file.suffix.upper().replace('.', '')
                
                analysis_data.append({
                    'filename': image_file.name,
                    'width': width,
                    'height': height,
                    'resolution': f"{width}×{height}",
                    'file_size_kb': file_size / 1024,
                    'format': format_type
                })
                
                total_size += file_size
                formats[format_type] = formats.get(format_type, 0) + 1
                resolutions[f"{width}×{height}"] = resolutions.get(f"{width}×{height}", 0) + 1
                
        except Exception as e:
            st.warning(f"无法分析图片 {image_file.name}: {str(e)}")
    
    return {
        'images': analysis_data,
        'total_count': len(analysis_data),
        'total_size_mb': total_size / (1024 * 1024),
        'avg_size_kb': (total_size / len(analysis_data)) / 1024 if analysis_data else 0,
        'formats': formats,
        'resolutions': resolutions
    }

def main():
    """
    主应用函数
    """
    # 标题
    st.title("📊 数据集可视化工具")
    st.markdown("---")
    
    # 侧边栏
    st.sidebar.title("⚙️ 控制面板")
    
    # 数据集路径选择
    dataset_path = st.sidebar.text_input("数据集路径", value="dataset-with-label")
    
    # 加载数据
    with st.spinner("正在加载数据集..."):
        categories_data, total_images = load_dataset_info(dataset_path)
    
    if categories_data is None:
        st.error(f"❌ 无法找到数据集路径: {dataset_path}")
        st.info("请确保路径正确，并且包含图片文件夹")
        return
    
    # 数据集概览
    st.header("📈 数据集概览")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("总样本数量", total_images)
    
    with col2:
        st.metric("类别数量", len(categories_data))
    
    with col3:
        if categories_data:
            avg_samples = total_images / len(categories_data)
            st.metric("平均每类样本数", f"{avg_samples:.1f}")
    
    # 详细统计表格
    st.subheader("📋 详细统计")
    
    if categories_data:
        # 创建数据框
        table_data = []
        for category, info in categories_data.items():
            percentage = (info['count'] / total_images * 100) if total_images > 0 else 0
            table_data.append({
                '英文名称': category,
                '中文名称': info['chinese_name'],
                '样本数量': info['count'],
                '占比(%)': f"{percentage:.1f}%"
            })
        
        df = pd.DataFrame(table_data)
        df = df.sort_values('样本数量', ascending=False)
        st.dataframe(df, use_container_width=True)
    
    # 可视化图表
    st.header("📊 数据分布可视化")
    
    chart_type = st.radio("选择图表类型", ["柱状图", "饼图"], horizontal=True)
    
    if chart_type == "柱状图":
        fig = create_distribution_chart(categories_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    else:
        fig = create_pie_chart(categories_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    # 样本浏览
    st.header("🖼️ 样本浏览")
    
    if categories_data:
        # 类别选择
        category_options = {info['chinese_name']: category 
                          for category, info in categories_data.items()}
        
        selected_chinese = st.selectbox(
            "选择要查看的类别",
            options=list(category_options.keys())
        )
        
        selected_category = category_options[selected_chinese] 
        
        # 显示选中类别的信息
        category_info = categories_data[selected_category]
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**类别**: {category_info['chinese_name']} ({selected_category})")
        with col2:
            st.info(f"**样本数量**: {category_info['count']}")
        
        # 显示控制选项
        col1, col2 = st.columns(2)
        
        with col1:
            # 样本数量选择
            max_samples = min(category_info['count'], 15)
            num_samples = st.slider("显示样本数量", 1, max_samples, min(9, max_samples))
        
        with col2:
            # 标注显示选项
            show_annotations = st.checkbox("显示详细标注", value=True)
        
        # 控制按钮
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 随机刷新样本"):
                st.cache_data.clear()
        
        with col2:
            # 网格列数选择
            grid_cols = st.selectbox("网格列数", [2, 3, 4], index=1)
        
        # 获取并显示样本图片
        with st.spinner("正在加载图片..."):
            sample_images = get_sample_images(
                Path(dataset_path) / selected_category, 
                num_samples
            )
        
        if sample_images:
            st.subheader(f"📷 {selected_chinese} 样本展示")
            display_image_grid(sample_images, cols=grid_cols, show_details=show_annotations)
        else:
            st.warning("没有找到图片文件")
        
        # 类别详细分析
        st.subheader(f"📊 {selected_chinese} 类别详细分析")
        
        with st.spinner("正在分析类别数据..."):
            analysis = analyze_category_images(Path(dataset_path) / selected_category)
        
        if analysis:
            # 基本统计
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("图片总数", analysis['total_count'])
            
            with col2:
                st.metric("总大小", f"{analysis['total_size_mb']:.1f} MB")
            
            with col3:
                st.metric("平均大小", f"{analysis['avg_size_kb']:.1f} KB")
            
            with col4:
                unique_resolutions = len(analysis['resolutions'])
                st.metric("分辨率种类", unique_resolutions)
            
            # 详细分析
            col1, col2 = st.columns(2)
            
            with col1:
                # 格式分布
                st.subheader("📋 格式分布")
                format_df = pd.DataFrame([
                    {'格式': format_type, '数量': count, '占比': f"{count/analysis['total_count']*100:.1f}%"}
                    for format_type, count in analysis['formats'].items()
                ])
                st.dataframe(format_df, use_container_width=True)
            
            with col2:
                # 分辨率分布
                st.subheader("📐 分辨率分布")
                resolution_df = pd.DataFrame([
                    {'分辨率': resolution, '数量': count, '占比': f"{count/analysis['total_count']*100:.1f}%"}
                    for resolution, count in sorted(analysis['resolutions'].items(), key=lambda x: x[1], reverse=True)[:10]
                ])
                st.dataframe(resolution_df, use_container_width=True)
            
            # 详细文件列表（可选展开）
            with st.expander("📂 查看完整文件列表"):
                files_df = pd.DataFrame(analysis['images'])
                files_df = files_df.rename(columns={
                    'filename': '文件名',
                    'width': '宽度',
                    'height': '高度', 
                    'resolution': '分辨率',
                    'file_size_kb': '大小(KB)',
                    'format': '格式'
                })
                files_df['大小(KB)'] = files_df['大小(KB)'].round(1)
                st.dataframe(files_df, use_container_width=True)
        
        else:
            st.error("无法分析类别数据")
    
    # 数据集质量分析
    st.header("🔍 数据集质量分析")
    
    if categories_data:
        # 数据均衡性分析
        counts = [info['count'] for info in categories_data.values()]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("最多样本类别", max(counts))
            st.metric("最少样本类别", min(counts))
        
        with col2:
            balance_ratio = min(counts) / max(counts) if max(counts) > 0 else 0
            st.metric("数据均衡度", f"{balance_ratio:.2f}")
            
            # 均衡度说明
            if balance_ratio > 0.8:
                st.success("✅ 数据分布较为均衡")
            elif balance_ratio > 0.5:
                st.warning("⚠️ 数据分布中等均衡")
            else:
                st.error("❌ 数据分布不均衡")
    
    # 页脚
    st.markdown("---")
    st.markdown("*数据集可视化工具 - 基于 Streamlit 构建*")

if __name__ == "__main__":
    main() 