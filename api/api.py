import win32api
import win32gui
import win32process
import pickle
import winsound
import pymem
import ctypes
from numpyencoder import NumpyEncoder
import time, json, math, random, numpy
# from frame_capture.frame import CSGO_FRAME

# csgo.json 是内存偏移 游戏更新时会改变；
# 自行更新 https://github.com/frk1/hazedumper/blob/master/csgo.json

def clip(num, max, min):
    if num > max:
        return max
    if num < min:
        return min
    return num

def normalizeAngles(viewAngleX, viewAngleY):
    if viewAngleX > 89:
        viewAngleX -= 360
    if viewAngleX < -89:
        viewAngleX += 360
    if viewAngleY > 180:
        viewAngleY -= 360
    if viewAngleY < -180:
        viewAngleY += 360

    return viewAngleX, viewAngleY

"""
用于测试的csgo账号（不要登录公网VAC服务器）:
账号:mmye252570
密码：ojpd6n9z

"""

class CSAPI:

    def __init__(self, path):
        with open(path) as conf:
            off_set_dict = json.load(conf)
        # self.FRAME = CSGO_FRAME(SHOW_IMAGE=False, IS_CONTRAST=True, rate=30)
        self.dwEntityList = int(off_set_dict["signatures"]["dwEntityList"])
        self.m_iHealth = int(off_set_dict["netvars"]["m_iHealth"])
        self.dwClientState_GetLocalPlayer = int(off_set_dict["signatures"]["dwClientState_GetLocalPlayer"])
        self.client_dll = 0
        self.handle = 0
        self.m_hActiveWeapon = int(off_set_dict["netvars"]["m_hActiveWeapon"])
        self.m_bSpotted = int(off_set_dict["netvars"]["m_bSpotted"])
        self.m_lifeState = int(off_set_dict["netvars"]["m_lifeState"])
        self.m_bDormant =int(off_set_dict["signatures"]["m_bDormant"])
        self.m_hMyWeapons = int(off_set_dict["netvars"]["m_hMyWeapons"])
        self.m_angEyeAnglesX = int(off_set_dict["netvars"]["m_angEyeAnglesX"])
        self.m_angEyeAnglesY = int(off_set_dict["netvars"]["m_angEyeAnglesY"])
        self.m_vecVelocity = int(off_set_dict["netvars"]["m_vecVelocity"])
        self.off_enginedll = 0
        self.m_dwBoneMatrix = int(off_set_dict["netvars"]["m_dwBoneMatrix"])
        self.m_iTeamNum = int(off_set_dict["netvars"]["m_iTeamNum"])
        self.dwClientState = int(off_set_dict["signatures"]["dwClientState"])
        self.dwClientState_ViewAngles = int(off_set_dict["signatures"]["dwClientState_ViewAngles"])
        self.m_vecOrigin = int(off_set_dict["netvars"]["m_vecOrigin"])
        self.m_vecViewOffset = int(off_set_dict["netvars"]["m_vecViewOffset"])
        self.m_iClip1= int(off_set_dict["netvars"]["m_iClip1"])
        self.dwLocalPlayer = int(off_set_dict["signatures"]["dwLocalPlayer"])
        self.dwForceAttack = int(off_set_dict["signatures"]["dwForceAttack"])
        self.dwForceAttack2 = int(off_set_dict["signatures"]["dwForceAttack2"])
        self.dwForceBackward = int(off_set_dict["signatures"]["dwForceBackward"])
        self.dwForceForward = int(off_set_dict["signatures"]["dwForceForward"])
        self.dwForceLeft = int(off_set_dict["signatures"]["dwForceLeft"])
        self.dwForceRight = int(off_set_dict["signatures"]["dwForceRight"])
        self.dwForceJump = int(off_set_dict["signatures"]["dwForceJump"])
        self.dwForceCrouch = int(off_set_dict["signatures"]["dwForceJump"]) + 0x24
        self.dwForceReload = int(off_set_dict["signatures"]["dwForceJump"]) + 0x30
        self.m_iItemDefinitionIndex=int(off_set_dict["netvars"]["m_iItemDefinitionIndex"])

        self.is_fire = 0
        self.enemy_heath = 100
        self.steps = 0



        # todo:自动导入csgo.json为本类属性

        # Counter-Strike: Global Offensive 窗口标题 获得窗口句柄
        window_handle = win32gui.FindWindow(None, u"Counter-Strike: Global Offensive - Direct3D 9")
        if window_handle:
            print(window_handle)
            # 获得窗口句柄获得进程ID
            process_id = win32process.GetWindowThreadProcessId(window_handle)
            print(process_id)
            handle = pymem.Pymem()
            handle.open_process_from_id(process_id[1])
            self.handle = handle
            # 遍历当前进程调用的dll，获得client.dll的基地址
            list_of_modules = handle.list_modules()

            while list_of_modules is not None:
                tmp = next(list_of_modules)
                if tmp.name == "client.dll":
                    self.client_dll = tmp.lpBaseOfDll
                if tmp.name == "engine.dll":
                    self.off_enginedll = tmp.lpBaseOfDll
                if self.off_enginedll != 0 and self.client_dll != 0:
                    break
            # client = pymem.process.module_from_name(
            #     handle.process_handle,
            #     "client.dll"
            # ).lpBaseOfDll
            # engine = pymem.process.module_from_name(
            #     handle.process_handle,
            #     "engine.dll"
            # ).lpBaseOfDll
            # print("off_enginedll,client_dll", engine, client)
        else:
            print("didn't get the window handle")
            exit()
        # todo:已经得到了基地址，加上任意偏移就可读写表地址的数值


    def get_health(self):
            # 获取当前人物血量
            player=0
            # 如果p 为0 则为 当前 人的血量
            entity = self.handle.read_bytes(self.client_dll + self.dwEntityList + player * 0x10, 4)  # 10为每个实体的偏移
            entity = int.from_bytes(entity, byteorder='little')
            if entity != 0:
                health = self.handle.read_bytes(entity + self.m_iHealth, 4)
                health = int.from_bytes(health, byteorder='little')
                return [health]

    def get_weapon(self):
            # todo: 武器内容比较复杂，每个武器都是个单独的对象，每个人物都拥有一个武器64位的指针列表
            """
                The m_hMyWeapons array contains handles to all weapons equipped by the local player.
                We can apply skin and model values to those weapons' entities independent to which weapon the local player is holding in hands.
                self.client_dll+self.dwLocalPlayer 获得当前用户的引用LOCAL
                LOCAL+m_hMyWeapons 获得当前用户的武器数组array。
                for 遍历（10）当前用户武器数组，获得武器实体的引用V（每个元素添加偏移0x4）
                V指针通过 dwEntityList + (currentWeapon - 1) * 0x10 获得当前武器的元信息；
                currentWeapon + m_iItemDefinitionIndex获得当前武器的 具体型号。

                C4:49
                匪徒刀：59
                CT刀：42
                p2000:32
                glock：4
                :return 返回长度为8的一个list
            """

            # if entity != 0:
            # 获取local基地址 self.client_dll + self.dwEntityList + 0*0x10
            local_add = self.handle.read_bytes(self.client_dll+self.dwLocalPlayer, 4)
            local_add = int.from_bytes(local_add, byteorder='little')
            # print(local_add)
            weapon_list=[0 for _ in range(8)]
            for i in range(8):
                # 武器数组array遍历获得武器引用。
                weapon_each = self.handle.read_bytes(local_add + self.m_hMyWeapons + i * 0x4, 4)
                weapon_each = int.from_bytes(weapon_each, byteorder='little') & 0xfff               # 我也不知道为什么按位与 1111
                # print("waepon_each:  " +  str(weapon_each))
                # 武器引用获得武器元信息。
                weapon_meta = self.handle.read_bytes(self.client_dll + self.dwEntityList + (weapon_each - 1) * 0x10, 4)
                weapon_meta = int.from_bytes(weapon_meta, byteorder='little')
                # print("weapon_meta:  " + str(weapon_meta))
                if weapon_meta == 0:
                    continue
                # # 武器元信息获得武器index。
                weapon_index = self.handle.read_int(weapon_meta+self.m_iItemDefinitionIndex)
                # print("weapon_index", weapon_index)
                weapon_list[i] = weapon_index
            return weapon_list

    def get_current_xy(self):
        """
        用于获得当前人物指针的指向，x轴(+180-180)，y轴(+-90)
        :return 返回长度为2的一个list
        """
        # player = 0
        # entity = self.handle.read_bytes(self.client_dll + self.dwEntityList + player * 0x10, 4)  # 10为每个实体的偏移
        # entity = int.from_bytes(entity, byteorder='little')
        # local_player = self.handle.read_uint(self.client_dll + self.dwLocalPlayer) # local_player 和entity_list[0]都为玩家
        # 玩家实体的地址，都为无符号整数uint而不是int。
        client_state = self.handle.read_uint(self.off_enginedll+self.dwClientState)
        view_x = self.handle.read_float((client_state + self.dwClientState_ViewAngles))
        view_y = self.handle.read_float((client_state + self.dwClientState_ViewAngles + 0x4))

        # print("client_state", client_state)
        # print("view_x, view_y", view_x, view_y)
        list = []
        # if entity != 0:
        #     x = self.handle.read_int((entity + self.m_angEyeAnglesX))
        #     x&=0x8000
        #
        #     y = self.handle.read_int(entity + self.m_angEyeAnglesY)
        #     y&=0x8000
        view_x, view_y = normalizeAngles(view_x, view_y)

        list.append(view_x)
        list.append(view_y)
        return list
    
    def get_current_position(self):
        """
        获得当前玩家的所在位置，两个维度
        :return:
        """

        list =[]
        aimlocalplayer = self.handle.read_int(self.client_dll+self.dwLocalPlayer)
        vecorigin = self.handle.read_int(aimlocalplayer + self.m_vecOrigin)

        localpos1 = self.handle.read_float(( aimlocalplayer + self.m_vecOrigin))  #+ self.handle.read_float(vecorigin + self.m_vecViewOffset + 0x104)
        localpos2 = self.handle.read_float(( aimlocalplayer + self.m_vecOrigin+0x4))   #+ self.handle.read_float(vecorigin + self.m_vecViewOffset + 0x108)
        localpos3 = self.handle.read_float((aimlocalplayer + self.m_vecOrigin + 0x8))  #+ self.handle.read_float(vecorigin + self.m_vecViewOffset + 0x10C)
        list.append(localpos1)
        list.append(localpos2)
        list.append(localpos3)
        return list

    def get_enemy_position(self):
        """
        输出 长度为15的数组，每三个代表一个敌人的位置，他们按照内存顺序排序

        :return:
        """
        # list=[0 for i in range(15)]
        list = []
        counter = 0
        aimlocalplayer = self.handle.read_int(self.client_dll+self.dwLocalPlayer)
        # 得到敌人的偏移
        my_team = self.handle.read_int(aimlocalplayer + self.m_iTeamNum)
        enemy_num = 0
        for i in range(64):

            entity = self.handle.read_bytes(self.client_dll + self.dwEntityList + i * 0x10, 4)  # 10为每个实体的偏移
            entity = int.from_bytes(entity, byteorder='little')
            if (entity != 0):  # 实体非空，则进行处理
                team = self.handle.read_int(entity + self.m_iTeamNum)
                # 实体 + 队伍偏移 == local_player + 队伍偏移 来判断是否是友军
                if (my_team == team):
                    # 友军
                    # 敌军
                    pass
                    # aimplayerbones = self.handle.read_int(entity + self.m_dwBoneMatrix)
                    # enemypos1 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x0C)
                    # enemypos2 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x1C)
                    # enemypos3 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x2C)
                    #
                    # list.append(enemypos1)
                    # list.append(enemypos2)
                    # list.append(enemypos3)
                    # enemy_num += 3
                else:
                    if counter < 5:
                        # # 敌军
                        aimplayerbones = self.handle.read_int(entity + self.m_dwBoneMatrix)
                        enemypos1 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x0C)
                        enemypos2 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x1C)
                        enemypos3 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x2C)
                        list.append(enemypos1)
                        list.append(enemypos2)
                        list.append(enemypos3)
                        counter += 1
        return  list

    def get_enemy_position_single(self):
        """
        输出 长度为15的数组，每三个代表一个敌人的位置，他们按照内存顺序排序

        :return:
        """
        # list=[0 for i in range(15)]
        list = []
        counter = 0
        aimlocalplayer = self.handle.read_int(self.client_dll+self.dwLocalPlayer)
        # 得到敌人的偏移
        my_team = self.handle.read_int(aimlocalplayer + self.m_iTeamNum)
        enemy_num = 0
        for i in range(64):

            entity = self.handle.read_bytes(self.client_dll + self.dwEntityList + i * 0x10, 4)  # 10为每个实体的偏移
            entity = int.from_bytes(entity, byteorder='little')
            if (entity != 0):  # 实体非空，则进行处理
                team = self.handle.read_int(entity + self.m_iTeamNum)
                # 实体 + 队伍偏移 == local_player + 队伍偏移 来判断是否是友军
                if (my_team == team):
                    # 友军
                    # 敌军
                    pass
                    # aimplayerbones = self.handle.read_int(entity + self.m_dwBoneMatrix)
                    # enemypos1 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x0C)
                    # enemypos2 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x1C)
                    # enemypos3 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x2C)
                    #
                    # list.append(enemypos1)
                    # list.append(enemypos2)
                    # list.append(enemypos3)
                    # enemy_num += 3
                else:
                    if counter < 1:
                        # # 敌军
                        aimplayerbones = self.handle.read_int(entity + self.m_dwBoneMatrix)
                        enemypos1 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x0C)
                        enemypos2 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x1C)
                        enemypos3 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x2C)
                        list.append(enemypos1)
                        list.append(enemypos2)
                        list.append(enemypos3)
                        counter += 1
        return  list


    def get_friendly_position(self):
        """
        输出 长度为15的数组，每三个代表一个敌人的位置，他们按照内存顺序排序
        友军位置，包括自己的位置
        :return:
        """
        # list=[0 for i in range(15)]
        list = []

        aimlocalplayer = self.handle.read_int(self.client_dll+self.dwLocalPlayer)
        # 得到人类的偏移
        my_team = self.handle.read_int(aimlocalplayer + self.m_iTeamNum)
        for i in range(64):
            entity = self.handle.read_bytes(self.client_dll + self.dwEntityList + i * 0x10, 4)  # 10为每个实体的偏移
            entity = int.from_bytes(entity, byteorder='little')
            if (entity != 0):  # 实体非空，则进行处理
                team = self.handle.read_int(entity + self.m_iTeamNum)
                # 实体 + 队伍偏移 == local_player + 队伍偏移 来判断是否是友军
                if (my_team == team):
                    # 友军
                    aimplayerbones = self.handle.read_int(entity + self.m_dwBoneMatrix)
                    pos1 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x0C)
                    pos2 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x1C)
                    pos3 = self.handle.read_float(aimplayerbones + 0x30 * 1 + 0x2C)
                    list.append(pos1)
                    list.append(pos2)
                    list.append(pos3)
                else:
                    # # 敌军
                   pass
        return  list

    def get_enemy_health(self):
        """
                输出 长度为5的数组,内存顺序排序
                :return:
                """
        # list=[0 for i in range(15)]
        list = []
        counter = 0
        aimlocalplayer = self.handle.read_int(self.client_dll + self.dwLocalPlayer)
        # 得到敌人的偏移
        my_team = self.handle.read_int(aimlocalplayer + self.m_iTeamNum)
        for i in range(64):
            entity = self.handle.read_bytes(self.client_dll + self.dwEntityList + i * 0x10, 4)  # 10为每个实体的偏移
            entity = int.from_bytes(entity, byteorder='little')
            if (entity != 0):  # 实体非空，则进行处理
                team = self.handle.read_int(entity + self.m_iTeamNum)
                # 实体 + 队伍偏移 == local_player + 队伍偏移 来判断是否是友军
                if (my_team == team):
                    # 友军
                    pass

                else:
                    if counter < 5:
                        # todo: 敌人血量，开局应重置为100
                        # # 敌军
                        # 获取当前人物血量
                        health = self.handle.read_bytes(entity + self.m_iHealth, 4)
                        health = int.from_bytes(health, byteorder='little')
                        list.append(health)
                        counter+=1
        return list

    def get_friendly_health(self):
        """
                输出 长度为5的数组,内存顺序排序
                :return:
                """
        # list=[0 for i in range(15)]
        list = []

        aimlocalplayer = self.handle.read_int(self.client_dll + self.dwLocalPlayer)
        # 得到敌人的偏移
        my_team = self.handle.read_int(aimlocalplayer + self.m_iTeamNum)
        for i in range(64):
            entity = self.handle.read_bytes(self.client_dll + self.dwEntityList + i * 0x10, 4)  # 10为每个实体的偏移
            entity = int.from_bytes(entity, byteorder='little')
            if (entity != 0):  # 实体非空，则进行处理
                team = self.handle.read_int(entity + self.m_iTeamNum)
                # 实体 + 队伍偏移 == local_player + 队伍偏移 来判断是否是友军
                if (my_team == team):
                    # 友军
                    # 获取当前人物血量
                    health = self.handle.read_bytes(entity + self.m_iHealth, 4)
                    health = int.from_bytes(health, byteorder='little')
                    list.append(health)
                else:
                    pass
        return list

    def set_attack2(self):
        # 测试中，无作用
        self.handle.write_int(self.client_dll + self.dwForceAttack2, -1)

    def set_attack(self, i):
        # 测试中，无作用
        self.is_fire = int(i)

        self.handle.write_int(self.client_dll + self.dwForceAttack, 6)
        # self.handle.write_int(self.client_dll + self.dwForceAttack, 0)

    def limit_aim(self, tar_dis):
        # [pitch, yaw]
        # +-90  +-180
        # 超出目标位置指定距离，重置到tar_dis范围，返回true


        # # 下面是重置代码，用于reset极端情况，避免不必要的训练
        # if pitch >= +80.0:
        #     print("protected!")
        #     self.aim_y = 80.0
        # if pitch <= -80.0:
        #     self.aim_y = -80.0
        #
        # if yaw >= +180:
        #     print("protected!")
        #     self.aim_x = 180.0
        # if yaw <= -180:
        #     print("protected!")
        #     self.aim_x = -180.0

        # 最优俯仰角
        pos = self.get_current_position()
        posx = pos[0]
        posy = pos[1]
        posz = pos[2]
        e_pos = self.get_enemy_position()
        e_posx = e_pos[0]
        e_posy = e_pos[1]
        e_posz = e_pos[2]
        targetline1 = e_posx - posx
        targetline2 = e_posy - posy
        targetline3 = e_posz - posz

        if targetline2 == 0 and targetline1 == 0:
            yaw = 0
            if targetline3 > 0:
                pitch = 270
            else:
                pitch = 90
        else:
            yaw = (math.atan2(targetline2, targetline1) * 180 / math.pi)
            if yaw < 0:
                yaw += 360
            hypotenuse = math.sqrt(
                (targetline1 * targetline1) + (targetline2 * targetline2) + (targetline3 * targetline3))
            pitch = (math.atan2(-targetline3, hypotenuse) * 180 / math.pi)
            if pitch < 0:
                pitch += 360

        pitch, yaw = normalizeAngles(pitch, yaw)
        cur = self.get_current_xy()
        cur_shang_xia = cur[0]
        cur_zuoyou = cur[1]

        #如果角度差距还大于tar_dis，则进行重置；重置到敌人脑袋附近
        if abs(cur_zuoyou - yaw) > tar_dis or abs(cur_shang_xia - pitch) > tar_dis:
            print("OUT RANGE RESET!!!!")
            self.set_aim([pitch + random.random()*10, yaw + random.random()*10])
            self.steps += 1
            return True

        self.steps += 1
        # print("steps: ", self.steps)
        return False


    def get_aim_dis(self):

        # 最优俯仰角
        pos = self.get_current_position()
        posx = pos[0]
        posy = pos[1]
        posz = pos[2]
        e_pos = self.get_enemy_position()
        e_posx = e_pos[0]
        e_posy = e_pos[1]
        e_posz = e_pos[2]
        targetline1 = e_posx - posx
        targetline2 = e_posy - posy
        targetline3 = e_posz - posz

        if targetline2 == 0 and targetline1 == 0:
            yaw = 0
            if targetline3 > 0:
                pitch = 270
            else:
                pitch = 90
        else:
            yaw = (math.atan2(targetline2, targetline1) * 180 / math.pi)
            if yaw < 0:
                yaw += 360
            hypotenuse = math.sqrt(
                (targetline1 * targetline1) + (targetline2 * targetline2) + (targetline3 * targetline3))
            pitch = (math.atan2(-targetline3, hypotenuse) * 180 / math.pi)
            if pitch < 0:
                pitch += 360

        pitch, yaw = normalizeAngles(pitch, yaw)
        cur = self.get_current_xy()
        cur_shang_xia = cur[0]
        cur_zuoyou = cur[1]

        return abs(cur_zuoyou - yaw) + abs(cur_shang_xia - pitch)


    def reset_aim(self):
        pos = self.get_current_position()
        posx = pos[0]
        posy = pos[1]
        posz = pos[2]
        e_pos = self.get_enemy_position()
        e_posx = e_pos[0]
        e_posy = e_pos[1]
        e_posz = e_pos[2]
        targetline1 = e_posx - posx
        targetline2 = e_posy - posy
        targetline3 = e_posz - posz

        if targetline2 == 0 and targetline1 == 0:
            yaw = 0
            if targetline3 > 0:
                pitch = 270
            else:
                pitch = 90
        else:
            yaw = (math.atan2(targetline2, targetline1) * 180 / math.pi)
            if yaw < 0:
                yaw += 360
            hypotenuse = math.sqrt(
                (targetline1 * targetline1) + (targetline2 * targetline2) + (targetline3 * targetline3))
            pitch = (math.atan2(-targetline3, hypotenuse) * 180 / math.pi)
            if pitch < 0:
                pitch += 360

        pitch, yaw = normalizeAngles(pitch, yaw)
        # print("RESET!!!!")
        self.set_aim([pitch + random.random() * 10, yaw + random.random() * 10])
        self.steps += 1



    def set_aim(self,list):
        aim_x = list[0]
        aim_y = list[1]
        enginepointer = self.handle.read_uint(self.off_enginedll + self.dwClientState)
        self.handle.write_float((enginepointer + self.dwClientState_ViewAngles), aim_x)
        self.handle.write_float((enginepointer + self.dwClientState_ViewAngles + 0x4), aim_y)

    def set_gym_aim(self, num):
        """
        num 0-4;up down left right still
        :param num:
        :return:
        """
        # get curr pich yaw
        client_state = self.handle.read_uint(self.off_enginedll+self.dwClientState)
        view_x = self.handle.read_float((client_state + self.dwClientState_ViewAngles))
        view_y = self.handle.read_float((client_state + self.dwClientState_ViewAngles + 0x4))
        view_x, view_y = normalizeAngles(view_x, view_y)
        # add action
        if num == 0:
            view_x = view_x + 2
        elif num==1:
            view_x = view_x - 2
        elif num==2:
            view_y = view_y + 2
        elif num == 3:
            view_y = view_y - 2
        self.set_aim([view_x, view_y])


    def set_walk(self,list):
        # wasd jump attack
        # 下蹲还没有做，正在探讨方法
        if len(list)!=6:
            print("WASD长度不为6")
        self.handle.write_int(self.client_dll + self.dwForceForward, list[0])
        self.handle.write_int(self.client_dll + self.dwForceBackward, list[1])
        self.handle.write_int(self.client_dll + self.dwForceLeft, list[2])
        self.handle.write_int(self.client_dll + self.dwForceRight, list[3])
        self.handle.write_int(self.client_dll + self.dwForceJump, list[4])
        if list[5]:
            self.handle.write_int(self.client_dll + self.dwForceAttack, 6)


    def get_reward(self):
        """
        奖励计算规则：
        +敌人血量与上一时间帧数之间血量的差值*800。
        #+100/当前瞄准和目标位置的XY轴距离。
        #-当前瞄准和目标位置的XY轴距离
        -固定偏移
        空枪惩罚

        :return:
        """
        total_blood = 0
        health_list = self.get_enemy_health()
        for each in health_list:
            total_blood += each
        # 这里计算血量减少的值作为奖赏
        blood_reward = abs(self.enemy_heath - total_blood)

        if blood_reward != 0:
            pass
            # print('blood_reward: ', blood_reward)
        self.enemy_heath = total_blood

        self.steps += 1
        reward = blood_reward*10 -1  #+ 10 (平常-1reward)
        #  超出目标距离给予惩罚
        is_reset = self.limit_aim(30) #30
        if is_reset:
            reward = blood_reward - 90
        # reward = reward - clip(self.get_aim_dis(), 20, 0)

        return reward, is_reset

    def get_best_aim(self):
        pos = self.get_current_position()
        posx = pos[0]
        posy = pos[1]
        posz = pos[2]
        e_pos = self.get_enemy_position()
        e_posx = e_pos[0]
        e_posy = e_pos[1]
        e_posz = e_pos[2]
        targetline1 = e_posx - posx
        targetline2 = e_posy - posy
        targetline3 = e_posz - posz

        if targetline2 == 0 and targetline1 == 0:
            yaw = 0
            if targetline3 > 0:
                pitch = 270
            else:
                pitch = 90
        else:
            yaw = (math.atan2(targetline2, targetline1) * 180 / math.pi)
            if yaw < 0:
                yaw += 360
            hypotenuse = math.sqrt(
                (targetline1 * targetline1) + (targetline2 * targetline2) + (targetline3 * targetline3))
            pitch = (math.atan2(-targetline3, hypotenuse) * 180 / math.pi)
            if pitch < 0:
                pitch += 360

        pitch, yaw = normalizeAngles(pitch, yaw)
        return [pitch,yaw]


    def get_all_situation(self):
        """
        [hp, view_y(pitch),view_x(yaw),  pos1,pos2,pos3  ,  my_weapon x 8 ,  enemy_position X 15 , enemy_health x 5]

        :return:
        """
        list = self.get_health() + self.get_current_xy() + self.get_current_position() + self.get_weapon() + self.get_enemy_position() + self.get_enemy_health()
        return list


    def get_aim_situation(self):
        """
        [view_y(pitch),view_x(yaw),  pos1,pos2,pos3  , enemy_position X 3 ] 8 维度
        """
        list = self.get_current_xy() + self.get_current_position() + self.get_enemy_position_single()
        aim = self.get_best_aim()
        list = [0.5*(math.sin(list[0])+1), 0.5*(math.cos(list[1])+1), 0.5*(math.sin(list[1])+1),
                0.5 * (math.sin(aim[0]) + 1), 0.5 * (math.cos(aim[1]) + 1), 0.5 * (math.sin(aim[1]) + 1)]
                # (650+list[2])/1300, (650+list[3])/1300, (1+list[4])*0.5,
                # (650+list[5])/1300, (650+list[6])/1300, (1+list[7])*0.5]
        return list

    # def get_aim_situation(self):
    #     """
    #     [ img_small, last_reward]
    #
    #             :return:
    #             """
    #     pic = self.FRAME.grab()
    #
    #     msg = {"pic": pic.tolist(), "reward": self.get_reward()}
    #
    #     return json.dumps(msg)


class CSEnv(object):
    def __init__(self, name):
        self.action_space = ["up", "down", "left", "right", "freeze", "fire"]
        self.observe_shape = [150, 280]
        self.name = name
        self.api = CSAPI(r"C:\Users\meng shi\PycharmProjects\pythonProject\csgo.json")

    def reset(self):
        self.api.reset_aim()
        return self.step(4)
    #
    # def render(self):
    #

    def step(self,action):
        " in: 0-5 up down left right still fire     out: obs, reward, done, info"
        if action == 5:
            self.api.set_attack(1)
        else:
            self.api.set_gym_aim(action)
        ob = self.api.get_aim_situation()
        reward, is_done = self.api.get_reward()
        return ob, reward, is_done, 0


if __name__ == '__main__':

    handle = CSAPI(r"..\api\csgo.json")
    params = {
        'gamma': 0.89,
        'epsi_high': 0.9,
        'epsi_low': 0.08,
        'decay': 800,  # 前期探索更充分一些
        'lr': 0.0003,
        'capacity': 60000,
        'batch_size': 800,  # 高一些能优化更准确
        'state_space_dim': 9,
        'action_space_dim': 6,
        'PATH': r"C:\Users\meng shi\PycharmProjects\gym\csgo_dqn\net_lr0.001_gamma0.89_ep2999.pth"
    }




