from telnetlib import COM_PORT_OPTION
import time
import platform
import os
import serial.tools.list_ports
from uarm.wrapper import SwiftAPI

class Arm:
    def __init__(self,COM=None):
        self.port = self.checkport(COM)
        self.arm = SwiftAPI(port=self.port, baudrate=115200)
        # 设置移动速度系数
        self.arm.set_speed_factor(100)
        # self.arm.set_speed(30)
        

    def checkport(self, COM):
        print('Checking Device...... \n')
        port = None
        if platform.system() == 'Windows':
            plist = list(serial.tools.list_ports.comports())
            if len(plist) <= 0:
                print ("The Serial port can't find!")
            else:
                plist_0 =list(plist[0])
                port= plist_0[0]
                print('Current device: ' + port + '\n')
        else:
            try:
                # 获取机械臂端口信息
                ret = os.popen("ls /dev/serial/by-id").read()
                port = "/dev/serial/by-id/" + ret.split('\n')[0].split('/')[-1]
                # 打印检测到的机械臂端口
                print('Current device: ' + port + '\n')
            except:
                print ("The Serial port can't find!")

        if port is not None:
            return port
        else:   
            return COM
    
    '''
    复位函数
    '''
    def Arm_Reset(self):
        # 复位
        self.arm.reset(speed=1000)
        # time.sleep(1)

    '''
    设置伺服连接函数
    '''
    def Arm_Set_servo_attach(self):
        self.arm.set_servo_attach()
        
    '''
    设置伺服断开函数
    '''
    def Arm_Set_servo_detach(self):
        self.arm.set_servo_detach()
        


    '''
    返回机械臂当前坐标
    '''
    def Arm_Get_Position(self):
        return self.arm.get_position()
        

    '''
    回归待抓取位置
    '''    
    def Arm_Beginning(self):
        self.arm.set_position(x=115, y=-3, z=45)

        


if __name__ == "__main__":
    
    Swift = Arm()
    # 复位
    Swift.Arm_Reset()
    #########################机械臂信息获取#############################
    # 获取电源状态
    print("电源状态:", Swift.arm.get_power_status())
    # 获取uArm信息
    print("uArm信息:", Swift.arm.get_device_info())
    # 获取吸盘限位开关的状态
    print("吸盘限位开关:",Swift.arm.get_limit_switch())
    # 获取电动夹状态 0: stop, 1: working, 2: catch thing
    print("电动夹状态:", Swift.arm.get_gripper_catch())
    # 获取吸盘状态 0: stop, 1: working, 2: catch thing
    print("吸盘状态:", Swift.arm.get_pump_status())
    # 获取模式状态
    print("uArm模式状态:", Swift.arm.get_mode())
    # 机械臂获取角度
    print("机械臂角度:", Swift.arm.get_servo_angle())
    # 角度、臂展距离、高度
    print("机械臂角度、臂展距离、高度:", Swift.arm.get_polar())
    # xyz坐标
    print("机械臂xyz坐标:", Swift.arm.get_position())


    #########################机械臂运动控制#############################
    # 设置速度
    Swift.arm.set_speed_factor(100)
    # Swift.arm.set_mode(mode=0)
    # 设置手腕角度 0-180
    Swift.arm.set_wrist(180)
    time.sleep(1)
    Swift.arm.set_wrist(90)
    # 控制蜂鸣器响默认1000HZ 
    Swift.arm.set_buzzer(frequency=1000)
    # 控制吸盘打开
    Swift.arm.set_pump(on=True)
    # 控制电动夹打开
    Swift.arm.set_gripper(catch=True)
    time.sleep(3)
    # 控制吸盘关闭
    Swift.arm.set_pump(on=False)
    # 控制电动夹关闭
    Swift.arm.set_gripper(catch=False)

    """
    控制移动 xyz坐标方式 y -100 |--------（0）---------| 100
                                        |
                                        |
                                        | x(0-350)
    """
    Swift.arm.set_position(x=200, y=0, z=100)
    time.sleep(2)
    print("当前机械臂xyz坐标:", Swift.arm.get_position())
    """
    控制移动（臂展距离、角度、高度）  方式 0 |--------（0）---------| 180
                                                    |
                                                    |
                                                    | (0-350)
    """
    Swift.arm.set_polar(stretch=200, rotation=90, height=150)
    time.sleep(2)
    """
    控制机械臂角度：
        servo_id=0， 控制底座，范围：0-180
        servo_id=1， 控制大臂，范围：25-130
        servo_id=2， 控制小臂，范围：跟大臂有关
    """
    Swift.arm.set_servo_angle(servo_id=0, angle=60)
