import torch
import torch.nn as nn

"""
forward函数用于定义神经网络模型的前向传播过程，
也就是描述输入数据如何通过网络的各个层和操作，最终生成输出结果

forward 函数是所有继承自 nn.Module 的 PyTorch 模型类必须实现的一个方法。
它的核心作用是指定输入数据在网络中的流动路径。
    例如，在一个简单的全连接神经网络中，
    forward 函数会定义输入数据如何依次通过输入层、隐藏层和输出层，
    最终得到预测结果。

在 PyTorch 中，当你使用 model(input) 调用模型时，实际上是在间接调用 forward 函数。
也就是说，model(input) 等价于 model.forward(input)。但为什么不直接调用 forward 方法呢？

这是因为 PyTorch 在 nn.Module 类中实现了 __call__ 方法。__call__ 不仅会执行 forward，
还会触发一些额外的操作，例如钩子函数（hooks）。这些钩子可以在训练过程中执行一些附加功能，
比如梯度裁剪或学习率调整。因此，建议始终使用 model(input) 而不是直接调用 model.forward(input)，
以确保这些附加功能能够正常运行。

"""

class unetConv2(nn.Module):
    """
    自定义的卷积块类，用于U-Net的编码器和解码器。
    """

    def __init__(self, in_size, out_size, is_batchnorm, n=3, ks=3, stride=1, padding=1):
        """

        :param in_size: 输入特征图的通道数
        :param out_size: 输出特征图的通道数
        :param is_batchnorm: 是否使用BatchNorm（批归一化）
        :param n: 卷积块中卷积层的个数
        :param ks: 卷积核大小
        :param stride: 卷积步长
        :param padding: 卷积填充大小
        """
        super(unetConv2, self).__init__()
        self.n = n
        self.ks = ks
        self.stride = stride
        self.padding = padding
        s = stride
        p = padding
        # 根据is_batchnorm参数选择是否使用BatchNorm，构建卷积块。
        # 使用nn.sequential()将多个层组合到一起，构建一个卷积块。
        # 使用setattr()函数动态创建并命名这些卷积块。
        if is_batchnorm:
            # True：Conv2d + BatchNorm2d + ReLU
            for i in range(1, n + 1):
                conv = nn.Sequential(nn.Conv2d(in_size, out_size, ks, s, p),
                                     nn.BatchNorm2d(out_size),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size

        else:
            # False：Conv2d + ReLU
            for i in range(1, n + 1):
                conv = nn.Sequential(nn.Conv2d(in_size, out_size, ks, s, p),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size

    def forward(self, inputs):
        """
        :param inputs: 来自上一层的特征图
        :return: 经过所有卷积块处理后的特征图
        """
        x = inputs
        for i in range(1, self.n + 1):
            conv = getattr(self, 'conv%d' % i)
            x = conv(x)

        return x


class unetUp(nn.Module):
    """
    自定义的上采样类，用于U-Net的解码器。
    负责将低分辨率的特征图上采样，并与编码器的高分辨率特征图拼接，
    然后进行卷积处理。
    """

    def __init__(self, in_size, out_size, is_deconv, n_concat=2):
        """
        :param in_size:  输入特征图的通道数
        :param out_size:  输出特征图的通道数
        :param is_deconv:  是否使用转置卷积
        :param n_concat:  拼接的特征图个数
        """
        super(unetUp, self).__init__()
        self.conv = unetConv2(in_size, out_size, False)
        if is_deconv:
            # 使用转置卷积
            self.up = nn.ConvTranspose2d(out_size, out_size, kernel_size=4, stride=2, padding=1)
        else:
            # 使用双线性插值上采样
            self.up = nn.UpsamplingBilinear2d(scale_factor=2)

    def forward(self, inputs0, *input):
        """
        对 inputs0 进行上采样，得到 outputs0。
        将 outputs0 与 *input 中的每个特征图在通道维度（dim=1）上拼接。
        *input 通常是来自编码器对应层的特征图，用于提供高分辨率的细节信息。
        将拼接后的特征图通过 unetConv2 进行卷积处理。
        :param inputs0: 输入的特征图
        :param input: 需要拼接的特征图
        :return: 经过卷积处理后的特征图
        """
        outputs0 = self.up(inputs0)
        for i in range(len(input)):
            outputs0 = torch.cat([outputs0, input[i]], 1)
        return self.conv(outputs0)


class UNet(nn.Module):

    def __init__(self, in_channels, n_classes, channels=64, is_deconv=True, is_batchnorm=True):
        """

        :param in_channels:  输入特征图的通道数
        :param n_classes:  输出分割图的类别数
        :param channels:  基础通道数
        :param is_deconv:  是否使用转置卷积
        :param is_batchnorm:  是否使用BatchNorm（批归一化）
        """
        super(UNet, self).__init__()
        self.is_deconv = is_deconv
        self.in_channels = in_channels
        self.is_batchnorm = is_batchnorm
        self.channels = channels
        self.n_classes = n_classes

        # 编码器部分，重复4次卷积操作，每次卷积后下采样。
        self.conv1 = unetConv2(self.in_channels, self.channels, self.is_batchnorm)
        self.maxpool1 = nn.MaxPool2d(kernel_size=2)

        self.conv2 = unetConv2(self.channels, self.channels, self.is_batchnorm)
        self.maxpool2 = nn.MaxPool2d(kernel_size=2)

        self.conv3 = unetConv2(self.channels, self.channels, self.is_batchnorm)
        self.maxpool3 = nn.MaxPool2d(kernel_size=2)

        self.conv4 = unetConv2(self.channels, self.channels, self.is_batchnorm)
        self.maxpool4 = nn.MaxPool2d(kernel_size=2)

        # 中心部分，对编码器最后的输出进行卷积处理，作为桥接编码器和解码器的部分。
        self.center = unetConv2(self.channels, self.channels, self.is_batchnorm)

        # 解码器部分，重复4次上采样操作，每次上采样后卷积。
        self.up_concat4 = unetUp(self.channels * 2, self.channels, self.is_deconv)
        self.up_concat3 = unetUp(self.channels * 2, self.channels, self.is_deconv)
        self.up_concat2 = unetUp(self.channels * 2, self.channels, self.is_deconv)
        self.up_concat1 = unetUp(self.channels * 2, self.channels, self.is_deconv)

        # 将解码器最后的特征图转换为分割图，通道数为 n_classes，使用3×3卷积核
        self.outconv1 = nn.Conv2d(self.channels, self.n_classes, 3, padding=1)

    def forward(self, inputs):
        """
        编码器: 数据依次通过 conv1 → maxpool1 → conv2 → maxpool2 →
                                         conv3 → maxpool3 → conv4 → maxpool4，
                                         提取特征并减小空间分辨率。
        中心: 通过 center 处理。
        解码器: 数据依次通过 up_concat4 → up_concat3 → up_concat2
                    → up_concat1，逐步上采样并结合编码器特征。
                    特征拼接（跳跃连接）用于融合深层语义信息和浅层细节信息。
        :param inputs:  输入的特征图
        :return:  分割结果，形状为 (batch_size, n_classes, height, width)。
        """
        conv1 = self.conv1(inputs)
        maxpool1 = self.maxpool1(conv1)

        conv2 = self.conv2(maxpool1)
        maxpool2 = self.maxpool2(conv2)

        conv3 = self.conv3(maxpool2)
        maxpool3 = self.maxpool3(conv3)

        conv4 = self.conv4(maxpool3)
        maxpool4 = self.maxpool4(conv4)

        center = self.center(maxpool4)

        up4 = self.up_concat4(center, conv4)
        up3 = self.up_concat3(up4, conv3)
        up2 = self.up_concat2(up3, conv2)
        up1 = self.up_concat1(up2, conv1)

        output = self.outconv1(up1)

        return output

