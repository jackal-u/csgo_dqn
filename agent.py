import torch, math, random
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim import lr_scheduler

import numpy,sys,pickle,datetime
from network import Net

torch.set_default_tensor_type(torch.FloatTensor)
device = 'cuda:0' if torch.cuda.is_available() else 'cpu'


class Agent:
    """
    输入维度：瞄准位置，自己位置，单个敌人位置，API行为奖励
    [view_y(pitch),view_x(yaw),  pos1,pos2,pos3  , enemy_position X 3 , reward x 1。 ] 9 维度
    输出维度： [ 6维度的大小不一的、action对应的Q值]
    """
    def __init__(self, **params):
        self.__dict__.update(params)
        net = Net()
        self.net = net.to(device)
        print("net: ", self.PATH)
        print("lr: ", self.lr)
        try:
            net.load_state_dict(torch.load(self.PATH))
            print("MODEL LOADED!")
        except:
            print("NO PREVIOUS MODEL")

        self.loss_cur_c = nn.MSELoss()
        self.optimizer = optim.Adam(net.parameters(), lr=float(self.lr))
        self.scheduler = lr_scheduler.StepLR(self.optimizer, step_size=9000, gamma=0.8)
        self.TOTAL_MEMORY = self.capacity
        self.buffer = []
        self.steps = 0
        self.old_obervation = []


    def act(self, s0):
        self.steps += 1
        epsi = self.epsi_low + (self.epsi_high - self.epsi_low) * (math.exp(-1.0 * self.steps / self.decay))
        if random.random() < epsi:
            a0 = random.randrange(0, 6)
        else:
            s0 = torch.tensor(s0, dtype=torch.float).view(1, -1)
            a0 = torch.argmax(self.net(s0)).item()
        return a0


    def put(self, *transition):
        if len(self.buffer) == self.TOTAL_MEMORY:
            self.buffer.pop(0)
        self.buffer.append(transition)


    def learn(self):
        if (len(self.buffer)) < self.batch_size : #or len(self.buffer) < self.random_max_step
            # 前n step 不学习
            return None, self.scheduler.get_lr()

        samples = random.sample(self.buffer, self.batch_size)
        s0, a0, r1, s1 = zip(*samples)
        s0 = torch.tensor(s0, dtype=torch.float)
        a0 = torch.tensor(a0, dtype=torch.long).view(self.batch_size, -1)
        r1 = torch.tensor(r1, dtype=torch.float).view(self.batch_size, -1)
        s1 = torch.tensor(s1, dtype=torch.float)

        y_true = r1 + self.gamma * torch.max(self.net(s1).detach(), dim=1)[0].view(self.batch_size, -1)
        y_pred = self.net(s0).gather(1, a0)

        loss_fn = nn.MSELoss()
        loss = loss_fn(y_pred, y_true)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.scheduler.step()
        return loss.item(), self.scheduler.get_lr()

