import os
import torch
import cv2 as cv
from .unet_lens import UNet
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

"""
总结性笔记 
`methods.py` 文件实现了一个完整的图像处理 lens_process，利用 UNet 模型进行语义分割，
并对分割结果进行后处理以提取和优化边界点集，最终在原始图像上可视化边界。
整个流程包括模型加载、图像预处理、模型预测、边界点提取、噪声去除、边界拟合和结果可视化。代码结构清晰，功能模块化，易于理解和扩展。
"""


class LensProcess:
    """
    图像处理管道类

    本类封装了对输入图像进行语义分割、边界点提取、噪声去除、二次多项式拟合
    及结果可视化和保存的完整流程。
    """

    def __init__(self, best_model_path, device=None):
        """
        初始化语义分割模型

        :param best_model_path: 最佳分割模型权重文件的路径
        :param device: 指定计算设备，若未指定则自动选择GPU（若可用）或CPU
        """
        # 1.1 确定计算设备（GPU或CPU）
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # 1.2 初始化UNet模型（in_channels=3, n_classes=2, channels=96）
        self.net = UNet(in_channels=3, n_classes=2, channels=96)
        # 1.3 加载预训练权重（weights_only方式）
        self.net.load_state_dict(torch.load(best_model_path, map_location=self.device, weights_only=True))
        self.net.to(self.device)
        self.net.eval()  # 设置为评估模式

    def unet_seg_method(self, image):
        """
        使用UNet模型对输入图像进行语义分割。

        :param image: 输入的原始图像，opencv读取，形状为(1024, 1440, 3)
        :return: 分割结果，形状为(1024, 1440)，每个像素的分类标签（0或1）
        """
        ##############################
        # 二、图像预处理
        ##############################
        # 2.1 调整通道顺序为 (C, H, W) 并转换为浮点型
        image = image.transpose(2, 0, 1).astype(np.float32)
        # 2.2 转换为PyTorch张量并添加批次维度
        image = torch.from_numpy(np.ascontiguousarray(image)).unsqueeze(0)
        # 2.3 将图像移到指定设备
        image = image.to(device=self.device, dtype=torch.float32)

        ##############################
        # 三、模型预测
        ##############################
        # 3.1 执行前向传播，获取预测结果
        with torch.no_grad():
            pred = self.net(image)
        # 3.2 取最大概率的类别并转换为numpy数组
        pred = torch.argmax(pred, dim=1)
        pred = pred.cpu().detach().numpy()[0, :, :]
        return pred

    @staticmethod
    def getUpAndDownPointerList(pred):
        """
        从UNet的分割结果中提取上边界和下边界点集。

        :param pred: UNet的分割结果，形状为(1024, 1440)，像素值为0或1
        :return: up_data: 上边界点集，形状为(N, 2)，每行是(x, y)
                 down_data: 下边界点集，形状为(M, 2)，每行是(x, y)
        """
        # 获取图像尺寸
        w, h = pred.shape

        ##############################
        # 一、下边界计算
        ##############################
        y_down = []
        x_down = []
        for i in range(h):
            now_i = pred[:, i]
            # 找到当前列中值为1的像素位置
            now_i = np.where(now_i == 1)[0]
            if len(now_i) != 0:
                # 取最后一个1作为下边界，y坐标取负值以适应图像坐标系
                y_down.append(-now_i[-1])
                x_down.append(i)
        down_data = np.array([x_down, y_down]).transpose(1, 0)

        ##############################
        # 二、上边界计算
        ##############################
        # 2.1 按列找到第一个值为1的位置（转为负值）
        y = (np.argmax(pred, axis=0) * -1).tolist()
        x_up_list = []
        y_up_list = []
        for i in range(len(y)):
            if y[i] != 0:  # 排除全为0的列
                y_up_list.append(y[i])
                x_up_list.append(i)
        up_data = np.array([x_up_list, y_up_list]).transpose(1, 0)
        return up_data, down_data

    @staticmethod
    def getBestDist(data, k):
        """
        计算每个点到其第k个最近邻的距离，用于DBSCAN的eps参数选择。

        :param data: 点集，形状为(N, 2)
        :param k: 第k个最近邻
        :return: k_dist: 每个点到其第k个最近邻的距离列表
        """
        k_dist = []
        for i in range(data.shape[0]):
            # 计算当前点与其他所有点的欧几里得距离
            dist = (((data[i] - data) ** 2).sum(axis=1) ** 0.5)
            dist.sort()  # 升序排序
            k_dist.append(dist[k])  # 取第k个距离
        return np.array(k_dist)

    @staticmethod
    def deleteErrorPointer(data, k=1, d=15):
        """
        使用DBSCAN算法去除点集中的噪声点。

        :param data: 待处理的点集，形状为(N, 2)
        :param k: DBSCAN的min_samples参数减1
        :param d: 用于选择eps的超参数
        :return: new_data: 去除噪声后的点集
        """
        ##############################
        # 一、DBSCAN算法
        ##############################
        # 1.1 计算每个点的k-近邻距离并排序
        k_dist = LensProcess.getBestDist(data, k)
        k_dist.sort()
        eps = k_dist[::-1][d]  # 倒序取第d个距离作为eps
        # 1.2 应用DBSCAN聚类
        dbscan_model = DBSCAN(eps=eps, min_samples=k + 1)
        label = dbscan_model.fit_predict(data)
        # 1.3 统计每个簇的点索引
        label_dist = {}
        for index, value in enumerate(label):
            if value not in label_dist:
                label_dist[value] = []
            label_dist[value].append(index)

        # 1.4 找出最大簇
        label_dist_len = {key: len(label_dist[key]) for key in label_dist}
        label_dist_list = sorted(label_dist_len.items(), key=lambda x: x[1])
        index_max_1 = label_dist_list[-1][0]  # 最大簇的标签
        new_data = data[label_dist[index_max_1]]
        # 1.5 如果最大簇点数不足一半，加入第二大簇
        if len(new_data) < len(data) / 2:
            index_max_2 = label_dist_list[-2][0]
            new_data = np.concatenate((new_data, data[label_dist[index_max_2]]))
        return new_data

    @staticmethod
    def fitEquation(data):
        """
        对点集进行二次多项式拟合，生成边界方程。

        :param data: 无噪声的点集，形状为(N, 2)
        :return: p1: 拟合的二次多项式函数
                 new_x, new_y: 拟合曲线上的点
        """
        # 分离x和y坐标
        x, y = data[:, 0], data[:, 1]
        # 进行二次多项式拟合
        z1 = np.polyfit(x, y, 2)
        p1 = np.poly1d(z1)
        # 计算拟合曲线的点
        new_x = x
        new_y = p1(new_x)
        return p1, new_x, new_y

    def process_and_save(self, image_path, save_dir):
        """
        完整图像处理流程：
          1. 读取并调整图像大小；
          2. 使用UNet模型进行语义分割；
          3. 提取上/下边界点集；
          4. 利用DBSCAN去除噪声；
          5. 对边界点进行二次多项式拟合；
          6. 在原始图像上绘制拟合结果；
          7. 保存最终结果图像到指定目录。

        :param image_path: 原始图像文件路径
        :param save_dir: 保存结果图像的文件夹路径
        """
        print(f"Processing image: {image_path}")
        # 读取图像并调整大小为 (1440, 1024)
        img = cv.imread(image_path)
        img = cv.resize(img, (1440, 1024))

        # -------------------------------
        # 语义分割
        # -------------------------------
        # 执行UNet语义分割，获得预测结果
        pred = self.unet_seg_method(img)
        # 可选：显示分割结果（注释掉的部分可根据需要打开）
        # plt.imshow(pred)
        # plt.title("Segmentation Result")
        # plt.show()

        # -------------------------------
        # 边界点提取
        # -------------------------------
        up_data, down_data = LensProcess.getUpAndDownPointerList(pred)
        # 可选：显示提取的边界点
        # plt.subplot(1, 2, 1)
        # plt.scatter(up_data[:, 0], up_data[:, 1])
        # plt.title("Upper Boundary Points")
        # plt.subplot(1, 2, 2)
        # plt.scatter(down_data[:, 0], down_data[:, 1])
        # plt.title("Lower Boundary Points")
        # plt.show()

        # -------------------------------
        # 上边界处理
        # -------------------------------
        # 去除噪声
        up_data = LensProcess.deleteErrorPointer(up_data, k=5, d=15)
        # 拟合上边界
        p1_up, up_x, up_y = LensProcess.fitEquation(up_data)
        # 在图像上绘制上边界拟合曲线（绿色圆点）
        for i in range(len(up_x)):
            cv.circle(img, (int(up_x[i]), int(-up_y[i])), 2, (0, 255, 0), -1)

        # -------------------------------
        # 下边界处理
        # -------------------------------
        # 去除噪声
        down_data = LensProcess.deleteErrorPointer(down_data)
        # 拟合下边界
        p1_down, down_x, down_y = LensProcess.fitEquation(down_data)
        # 在图像上绘制下边界拟合曲线（绿色圆点）
        for i in range(len(down_x)):
            cv.circle(img, (int(down_x[i]), int(-down_y[i])), 2, (0, 255, 0), -1)

        # -------------------------------
        # 保存结果
        # -------------------------------
        # 获取原文件名（不含路径）
        filename = os.path.basename(image_path)
        # 分离文件名和扩展名
        name, ext = os.path.splitext(filename)
        # 生成新的文件名，例如 "1-1-output.jpg"
        new_filename = f"{name}-output{ext}"
        # 组合保存路径
        save_path = os.path.join(save_dir, new_filename)
        cv.imwrite(save_path, img)
        print(f"Image saved to: {save_path}")

        # 可选：显示最终结果和其他中间结果（可根据需要取消注释）
        # cv.imshow('原始图像', img)
        # cv.imshow('分割结果', (pred * 255).astype(np.uint8))  # 假设 pred 是 0/1 的掩膜
        # cv.waitKey(0)
        # cv.destroyAllWindows()
        # plt.close('all')  # 确保关闭所有 matplotlib 窗口


# 主程序入口
if __name__ == "__main__":
    # 指定最佳模型路径
    best_model_path = "../models/lens.pth"
    # 实例化图像处理管道类
    lens_process = LensProcess(best_model_path)
    # 指定输入图像路径
    image_path = r"D:\Code\PyCharm_ws\medical_image_analyzer\data\lens\1-1.jpg"
    # 指定结果保存目录
    save_dir = r"D:\Code\PyCharm_ws\medical_image_analyzer\output\lens"
    # 调用处理流程并保存结果
    lens_process.process_and_save(image_path, save_dir)
