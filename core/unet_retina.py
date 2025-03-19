import torch
import torch.nn as nn

"""
forward函数用于定义神经网络模型的前向传播过程，
即描述输入数据如何依次通过网络各层操作，最终生成输出结果。

在 PyTorch 中，当调用 model(input) 时，实际上会自动触发 forward 方法，
并执行一些额外的操作（例如 hooks），因此建议始终使用 model(input) 来调用模型。
"""

class DoubleConv(nn.Module):
    """
    DoubleConv类实现了连续两次卷积操作，
    每次卷积后均接一个BatchNorm层和ReLU激活函数，
    用于在提取特征的同时进行非线性变换。

    :param in_channels: 输入特征图的通道数
    :param out_channels: 输出特征图的通道数
    :param mid_channels: 中间卷积层的通道数，默认为None，此时取out_channels
    """
    def __init__(self, in_channels, out_channels, mid_channels=None):
        super().__init__()
        if not mid_channels:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        """
        前向传播：将输入x依次经过两次卷积、BatchNorm和ReLU激活函数的处理，
        返回处理后的特征图。

        :param x: 输入特征图
        :return: 经过双卷积处理后的特征图
        """
        return self.double_conv(x)


class Down(nn.Module):
    """
    Down类实现下采样操作，
    通过最大池化减少特征图的空间尺寸，
    并利用DoubleConv提取下采样后的特征。

    :param in_channels: 输入特征图的通道数
    :param out_channels: 输出特征图的通道数
    """
    def __init__(self, in_channels, out_channels):
        super().__init__()
        # 先进行2×2最大池化，再进行双卷积操作
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 2), padding=(0, 0)),
            DoubleConv(in_channels, out_channels)
        )

    def forward(self, x):
        """
        前向传播：先通过最大池化降低空间分辨率，再通过双卷积提取特征。

        :param x: 输入特征图
        :return: 下采样后的特征图
        """
        return self.maxpool_conv(x)


class Up(nn.Module):
    """
    Up类实现上采样操作，
    通过双线性插值将特征图上采样到目标尺寸，
    并与编码器对应层的特征图拼接，
    最后通过DoubleConv融合拼接后的特征。

    :param in_channels: 拼接后输入的通道数
    :param out_channels: 输出特征图的通道数
    """
    def __init__(self, in_channels, out_channels):
        super().__init__()
        # 使用in_channels // 2作为中间通道数进行双卷积操作
        self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)

    def forward(self, x1, x2):
        """
        前向传播过程：
        1. 对x1（低分辨率特征图）进行双线性插值上采样，使其尺寸与x2一致。
        2. 将上采样后的x1与x2在通道维度（dim=1）上拼接，
           融合解码器和编码器的信息。
        3. 将拼接后的特征图通过双卷积模块进行进一步融合。

        :param x1: 较低分辨率的特征图（来自解码器）
        :param x2: 对应较高分辨率的特征图（来自编码器）
        :return: 融合后的特征图
        """
        # 上采样x1到与x2相同的空间尺寸
        x1 = torch.nn.functional.interpolate(input=x1, size=(x2.shape[2], x2.shape[3]),
                                               mode='bilinear', align_corners=False)
        # 在通道维度上拼接x2和上采样后的x1
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class OutConv(nn.Module):
    """
    OutConv类用于将最后的特征图映射为最终的分割结果，
    采用1×1卷积，将特征图的通道数转换为目标类别数。

    :param in_channels: 输入特征图的通道数
    :param out_channels: 输出分割图的类别数
    """
    def __init__(self, in_channels, out_channels):
        super(OutConv, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x):
        """
        前向传播：通过1×1卷积将输入特征图映射为分割结果，
        每个像素点的通道数表示对应类别的得分。

        :param x: 输入特征图
        :return: 分割结果
        """
        return self.conv(x)


class UNet(nn.Module):
    """
    UNet类实现了基于U-Net结构的分割网络，
    包括编码器、桥接层和解码器，通过跳跃连接融合多尺度特征，
    最终生成高精度的分割图。

    :param n_channels: 输入图像的通道数，默认1（灰度图）
    :param n_classes: 输出分割图的类别数，默认3
    """
    def __init__(self, n_channels=1, n_classes=3):
        super(UNet, self).__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes

        # 编码器部分：逐层下采样并提取特征
        self.inc = DoubleConv(n_channels, 64)      # 初始双卷积
        self.down1 = Down(64, 128)                   # 第一次下采样，特征通道数增至128
        self.down2 = Down(128, 256)                  # 第二次下采样，特征通道数增至256
        self.down3 = Down(256, 512)                  # 第三次下采样，特征通道数增至512
        self.down4 = Down(512, 1024)                 # 第四次下采样，特征通道数增至1024
        self.down5 = Down(1024, 2048 // 2)           # 第五次下采样，2048取半得到1024

        # 解码器部分：逐层上采样并融合对应的编码器特征（跳跃连接）
        self.up1 = Up(2048, 1024 // 2)               # 第一次上采样
        self.up2 = Up(1024, 512 // 2)                # 第二次上采样
        self.up3 = Up(512, 256 // 2)                 # 第三次上采样
        self.up4 = Up(256, 128 // 2)                 # 第四次上采样
        self.up5 = Up(128, 64)                       # 第五次上采样

        # 输出层：通过1×1卷积将最终特征图映射为分割结果
        self.outc = OutConv(64, n_classes)

    def forward(self, x):
        """
        前向传播过程说明：
        1. 编码器：输入图像依次通过初始双卷积和多次下采样模块，
           提取多尺度特征并降低空间分辨率。
        2. 解码器：依次上采样，并将上采样特征与编码器对应层的特征进行拼接，
           通过双卷积融合信息。
        3. 输出层：将融合后的特征图通过1×1卷积映射为分割结果。

        :param x: 输入图像，形状为 (batch_size, n_channels, height, width)
        :return: 分割结果，形状为 (batch_size, n_classes, height, width)
        """
        # 编码器部分
        x1 = self.inc(x)       # 初始双卷积，输出通道数为64
        x2 = self.down1(x1)    # 下采样，输出通道数为128
        x3 = self.down2(x2)    # 下采样，输出通道数为256
        x4 = self.down3(x3)    # 下采样，输出通道数为512
        x5 = self.down4(x4)    # 下采样，输出通道数为1024
        x6 = self.down5(x5)    # 下采样，输出通道数为1024

        # 解码器部分，通过上采样逐步恢复空间分辨率并融合编码器特征
        x = self.up1(x6, x5)   # 上采样并拼接x5
        x = self.up2(x, x4)    # 上采样并拼接x4
        x = self.up3(x, x3)    # 上采样并拼接x3
        x = self.up4(x, x2)    # 上采样并拼接x2
        x = self.up5(x, x1)    # 上采样并拼接x1

        logits = self.outc(x)  # 输出层，映射为分割结果
        return logits
