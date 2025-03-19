#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
core/analyzer.py
整合医学图像识别的核心处理逻辑，包含晶状体与视网膜两部分的处理流程。
默认模型和BM层数据分别放置在./models和./data目录下。
"""

import os
import sys
import time
import logging
import cv2
import numpy as np
import torch
import matplotlib.pyplot as plt
from scipy.spatial import distance
from sklearn.cluster import DBSCAN

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# ---------------------
# 公共工具函数
# ---------------------
def safe_imread(path, flags=cv2.IMREAD_COLOR):
    """
    安全加载图像，如果加载失败则退出程序。
    """
    img = cv2.imread(path, flags)
    if img is None:
        logging.error("无法加载图像: %s", path)
        sys.exit(1)
    return img

# ---------------------
# 晶状体（Lens）部分函数
# ---------------------
def unet_segmentation(img, model, target_size=(1440, 1024)):
    """
    使用预训练UNet模型对输入图像进行分割。
    输入:
        img: cv2读取的BGR图像
        model: 已加载权重的UNet模型
        target_size: 模型期望的输入尺寸 (宽, 高)
    输出:
        pred: 分割结果mask (二维数组)
    """
    device = next(model.parameters()).device
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, target_size)
    img_tensor = torch.from_numpy(img_resized.transpose(2, 0, 1).astype(np.float32))
    img_tensor = img_tensor.unsqueeze(0).to(device)
    with torch.no_grad():
        pred = model(img_tensor)
        pred = torch.argmax(pred, dim=1)
        pred = pred.cpu().numpy()[0]
    logging.info("UNet分割完成")
    return pred

def extract_boundaries(pred):
    """
    从分割mask中提取上、下边界点集。
    输出:
        up_data: 上边界点集合 (N,2)
        down_data: 下边界点集合 (N,2)
    """
    h, w = pred.shape
    x_down, y_down = [], []
    for i in range(w):
        col = pred[:, i]
        idx = np.where(col == 1)[0]
        if idx.size:
            x_down.append(i)
            y_down.append(-idx[-1])
    down_data = np.array([x_down, y_down]).T

    x_up, y_up = [], []
    col_argmax = np.argmax(pred, axis=0)
    for i, val in enumerate(col_argmax):
        if val != 0:
            x_up.append(i)
            y_up.append(-val)
    up_data = np.array([x_up, y_up]).T
    logging.info("边界提取完成: 上边界点数 %d, 下边界点数 %d", up_data.shape[0], down_data.shape[0])
    return up_data, down_data

def compute_k_distances(data, k=1):
    """
    计算每个点到第k近邻的欧氏距离，向量化实现。
    """
    diff = data[:, np.newaxis, :] - data[np.newaxis, :, :]
    dists = np.linalg.norm(diff, axis=2)
    dists.sort(axis=1)
    return dists[:, k]

def remove_noise(data, k=1, d=15):
    """
    利用DBSCAN降噪。
    参数：
        k: 计算近邻时采用的近邻个数
        d: 选择eps参数的启发式值（从排序后的距离中反向取第d个）
    """
    k_dists = compute_k_distances(data, k)
    k_dists_sorted = np.sort(k_dists)
    eps = k_dists_sorted[::-1][d]
    logging.info("DBSCAN eps: %.4f", eps)
    dbscan = DBSCAN(eps=eps, min_samples=k+1)
    labels = dbscan.fit_predict(data)
    label_dict = {}
    for idx, lab in enumerate(labels):
        label_dict.setdefault(lab, []).append(idx)
    largest_label = max(label_dict, key=lambda x: len(label_dict[x]))
    new_data = data[label_dict[largest_label]]
    if len(new_data) < len(data) / 2 and len(label_dict) > 1:
        sorted_labels = sorted(label_dict.items(), key=lambda x: len(x[1]), reverse=True)
        new_indices = sorted_labels[0][1] + sorted_labels[1][1]
        new_data = data[new_indices]
    logging.info("降噪后点数: %d", new_data.shape[0])
    return new_data

def fit_boundary(data):
    """
    对降噪后的边界点进行二次多项式拟合。
    输出:
        poly_func: 拟合的多项式函数对象
        x_fit, y_fit: 拟合曲线的坐标
    """
    x = data[:, 0]
    y = data[:, 1]
    coeffs = np.polyfit(x, y, 2)
    poly_func = np.poly1d(coeffs)
    y_fit = poly_func(x)
    logging.info("拟合系数: %s", coeffs)
    return poly_func, x, y_fit

def process_lens(lens_image_path, target_size=(1440, 1024)):
    """
    晶状体处理流程：
        1. 加载图像和默认预训练UNet模型（路径：./models/lens.pth）
        2. 分割图像，提取边界，降噪和拟合边界
        3. 可视化分割与拟合结果
    """
    logging.info("处理晶状体图像: %s", lens_image_path)
    img = safe_imread(lens_image_path, cv2.IMREAD_COLOR)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    try:
        from unet_lens import UNet
    except ImportError:
        logging.error("无法导入UNet模块，请检查unet.py文件")
        sys.exit(1)
    # 使用默认模型文件路径
    default_model_path = os.path.join("models", "lens.pth")
    model = UNet(in_channels=3, n_classes=2, channels=96)
    try:
        model.load_state_dict(torch.load(default_model_path, map_location=device))
    except Exception as e:
        logging.error("加载模型失败: %s", e)
        sys.exit(1)
    model.to(device)
    model.eval()
    pred = unet_segmentation(img, model, target_size)
    plt.figure()
    plt.title("Lens Segmentation")
    plt.imshow(pred, cmap='gray')
    plt.axis('off')
    plt.show()
    up_data, down_data = extract_boundaries(pred)
    fig, axs = plt.subplots(1, 2, figsize=(12, 6))
    axs[0].scatter(up_data[:, 0], up_data[:, 1], s=1, c='g')
    axs[0].set_title("Upper Boundary Points")
    axs[1].scatter(down_data[:, 0], down_data[:, 1], s=1, c='b')
    axs[1].set_title("Lower Boundary Points")
    for ax in axs:
        ax.axis('off')
    plt.show()
    up_data_clean = remove_noise(up_data, k=5, d=15)
    poly_func, x_fit, y_fit = fit_boundary(up_data_clean)
    img_copy = img.copy()
    for i in range(len(x_fit)):
        cv2.circle(img_copy, (int(x_fit[i]), int(-y_fit[i])), 2, (0, 255, 0), -1)
    plt.figure()
    plt.title("Fitted Upper Boundary on Lens")
    plt.imshow(cv2.cvtColor(img_copy, cv2.COLOR_BGR2RGB))
    plt.axis('off')
    plt.show()
    logging.info("晶状体处理完成")

# ---------------------
# 视网膜（Retina）部分函数
# ---------------------
def load_bm_layer(bm_layer_path=None):
    """
    加载BM层数据（.npy格式），转换为 (N,2) 点集。
    默认路径：./data/4.npy
    """
    if bm_layer_path is None or bm_layer_path == "":
        bm_layer_path = os.path.join("data", "4.npy")
    try:
        bm_layer = np.load(bm_layer_path)
    except Exception as e:
        logging.error("加载BM层数据失败: %s", e)
        sys.exit(1)
    bm_layer = np.array([(x, y) for x, y in enumerate(bm_layer[0])])
    logging.info("BM层数据加载成功，点数: %d", bm_layer.shape[0])
    return bm_layer

def generate_candidate_circles(radius_range, center_x_range, center_y_range, step):
    """
    根据指定范围生成候选圆集合，每个候选圆由 (cx, cy, r) 表示。
    """
    circles = []
    for r in radius_range:
        for cx in range(center_x_range[0], center_x_range[1], step):
            for cy in range(center_y_range[0], center_y_range[1], step):
                circles.append((cx, cy, r))
    logging.info("生成候选圆数量: %d", len(circles))
    return circles

def compute_circle_fitting_score(bm_layer, circle):
    """
    计算BM层点集与候选圆的拟合得分：BM层各点到圆周的最小距离均值。
    """
    cx, cy, r = circle
    theta = np.linspace(0, 2 * np.pi, 100)
    circle_points = np.array([(cx + r * np.cos(t), cy + r * np.sin(t)) for t in theta])
    dists = distance.cdist(bm_layer, circle_points, 'euclidean')
    score = np.mean(np.min(dists, axis=1))
    return score

def find_best_circle(bm_layer, circles):
    """
    在候选圆中寻找拟合得分最低的圆。
    """
    best_circle = None
    best_score = float('inf')
    for circle in circles:
        score = compute_circle_fitting_score(bm_layer, circle)
        if score < best_score:
            best_score = score
            best_circle = circle
    logging.info("最佳圆拟合得分: %.4f", best_score)
    return best_circle

def process_retina(bscan_image_path, bm_layer_path=""):
    """
    视网膜处理流程：
        1. 加载默认BM层数据（路径：./data/4.npy）和用户选择的B-scan图像
        2. 生成候选圆并寻找最佳拟合圆
        3. 可视化BM层数据与拟合圆
    """
    logging.info("处理视网膜图像，B-scan: %s", bscan_image_path)
    bm_layer = load_bm_layer(bm_layer_path)
    bscan_image = safe_imread(bscan_image_path, cv2.IMREAD_GRAYSCALE)
    # 候选圆参数（可根据实际情况调整）
    radius_range = range(200, 350, 5)
    center_x_range = (0, 400)
    center_y_range = (0, 640)
    step = 20
    circles = generate_candidate_circles(radius_range, center_x_range, center_y_range, step)
    best_circle = find_best_circle(bm_layer, circles)
    if best_circle:
        cx, cy, r = best_circle
        logging.info("最佳圆: Center=(%d, %d), Radius=%d", cx, cy, r)
        plt.figure(figsize=(10, 6))
        plt.imshow(bscan_image, cmap='gray')
        plt.plot(bm_layer[:, 0], bm_layer[:, 1], 'r-', label='BM Layer')
        circle_patch = plt.Circle((cx, cy), r, color='b', fill=False,
                                  label=f'Best Fit Circle (r={r/10:.2f}mm)')
        plt.gca().add_patch(circle_patch)
        plt.scatter(cx, cy, color='y')
        plt.legend()
        plt.title("BM Layer and Best Fit Circle")
        plt.axis('off')
        plt.show()
    else:
        logging.warning("未找到合适的拟合圆")
    logging.info("视网膜处理完成")

# ---------------------
# 整合分析器类
# ---------------------
class MedicalImageAnalyzer:
    def __init__(self, device=None):
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logging.info("使用设备: %s", self.device)

    def process_all(self, lens_image_path, bscan_image_path):
        """
        整体处理流程：
          - 晶状体部分：使用用户选择的图像，默认加载模型（./models/lens.pth）
          - 视网膜部分：使用用户选择的B-scan图像，默认加载BM层数据（./data/4.npy）
        """
        start_time = time.time()
        logging.info("开始整体处理流程...")
        process_lens(lens_image_path)
        process_retina(bscan_image_path)
        elapsed = time.time() - start_time
        logging.info("整体处理流程完成，总耗时: %.2f秒", elapsed)
