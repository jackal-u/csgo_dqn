import torch, math, random
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim import lr_scheduler

import numpy,sys,pickle,datetime


torch.set_default_tensor_type(torch.FloatTensor)
device = 'cuda:0' if torch.cuda.is_available() else 'cpu'


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        # input 34 list - 5 hp
        # self.bn0 = nn.BatchNorm1d(8)
        self.fc1 = nn.Linear(6, 50)
        # self.bn1 = nn.BatchNorm1d(50)
        self.fc2 = nn.Linear(50, 50)
        self.fc3 = nn.Linear(50, 50)
        self.fc4 = nn.Linear(50, 50)
        # self.fc3 = nn.Linear(1000, 200)
        self.fc5 = nn.Linear(50, 6)


    def forward(self, x):
        """
        如何解决loss爆炸问题？
        1.LR太高  调整为0.001 情况依然存在
        2.网络太长
        3，BN在捣乱
        4，reward给的太多 这是存在可能的，reward值应当在一个合理范围，目前reward值都是-600级别的。我仔细观察了一下，发现AI实际瞄准很接近了，但是瞄准角敌人在+170，AI瞄准的角在-170和+170之间抖动，这样会造成奖励函数异常！很有可能是奖励函数设置错了。应当取绝对值！
        :param x:
        :return:
        """
        x = torch.sigmoid(self.fc1(x)) #F.relu

        x = self.fc2(x)
        # x = F.relu(self.fc3(x))
        x = torch.sigmoid(self.fc3(x))
        x = torch.sigmoid(self.fc3(x))
        x = torch.sigmoid(self.fc3(x))
        x = torch.sigmoid(self.fc3(x))
        x = torch.sigmoid(self.fc3(x))
        x = torch.sigmoid(self.fc4(x))
        x = self.fc5(x)


        return x


