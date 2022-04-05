import torch, math, random
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim import lr_scheduler
import numpy,sys,pickle,datetime
from agent import *
from api.api import CSEnv
import statistics
import copy


torch.set_default_tensor_type(torch.FloatTensor)


device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
def draw(score,mean, total_loss, lr, act):
    import matplotlib.pyplot as plt
    total_loss = total_loss[-100:]
    plt.subplot(2, 2, 1)
    plt.plot([i for i in range(len(score))], score, 'g', label="origin")
    plt.plot([i for i in range(len(mean))], mean, 'b', label="last 100 mean")
    plt.axis([0, len(score), min(score), max(score) + 4])
    plt.title("EPreward")

    plt.subplot(222)
    plt.plot([i for i in range(len(lr))], lr, 'y')
    plt.axis([0, len(lr), min(lr), max(lr)])
    plt.title("lr ep")

    plt.subplot(223)
    plt.plot([i for i in range(len(total_loss))], total_loss, 'r')
    plt.axis([0, len(total_loss), min(total_loss), max(total_loss)+4])
    plt.title("mean_loss ep")

    plt.subplot(224)
    a0,a1,a2,a3,a4,a5 = act.count(0),act.count(1),act.count(2),act.count(3),act.count(4),act.count(5)
    plt.bar(["down","up","left","right","still","fire"], [a0,a1,a2,a3,a4,a5])

    plt.title("act step")

    plt.show()


def start():
        env = CSEnv("csgo")

        params = {
            'gamma': 0.89,
            'epsi_high': 0.9,
            'epsi_low': 0.08,
            'decay': 800,  # 前期探索更充分一些
            'lr': 0.001,
            'capacity': 30000,
            'batch_size': 800,  # 高一些能优化更准确
            'state_space_dim': 9,
            'action_space_dim': 6,
            'PATH': r"./.pth"
        }
        agent = Agent(**params)

        score = []
        mean = []
        ep_loss = []
        total_loss = []
        total_lr = []
        total_a0 = []


        for episode in range(5000):
            s0, _, _, _ = env.reset()
            total_reward = 1
            for i in range(80):
                a0 = agent.act(s0)

                total_a0.append(a0)

                s1, r1, done, _ = env.step(a0)

                # if done:
                #     r1 = -50  #本来设置了重置惩罚-50 但是这里被设为1

                agent.put(s0, a0, r1, s1)

                total_reward += r1

                s0 = copy.deepcopy(s1)
                if done:
                    # 之前done的太早，结束的reward没有纳入统计
                    break
                # s0 = s1
                # learn
                loss, lr = agent.learn()
                if loss:
                    ep_loss.append(loss)

            score.append(total_reward)
            mean.append(sum(score[-100:]) / 100)
            total_loss.append(statistics.mean(ep_loss) if ep_loss else 0)
            total_lr.append(lr[0])

            print("total_reward: ", total_reward)

        draw(score, mean, total_loss,total_lr,total_a0)
        torch.save(agent.net.state_dict(), "net_lr{}_gamma{}_ep{}.pth".format(agent.lr,agent.gamma,episode))

if __name__ == '__main__':
    start()







