# -*- encoding: UTF-8 -*-
import sys
import os
import threading
import time

# Lấy đường dẫn tương đối của thư mục chứa file2.py
current_directory = os.path.dirname(__file__)

# Thêm đường dẫn của thư mục chứa file1.py vào sys.path
sys.path.append(os.path.abspath(os.path.join(current_directory, '', 'code_dieuKhien')))
sys.path.append(os.path.abspath(os.path.join(current_directory, '', 'code_xuLyAnh')))

import Nao_header
import Nao_move
import Nao_camera

print("Stand up !")
Nao_header.Nao_stand_up()

print("Cui !")
Nao_header.Nao_cuidau()
Nao_move.Nao_tienThang(1,1,0)
time.sleep(10)

print("start task")

def detect_nao():
    Nao_camera.Nao_camera_detect()

def vantoc(m):
    if m > 10:
        return 0.5
    if m < -10:
        return -0.5

def control_nao():
    while(1):
        x,y,e = Nao_camera.data_canh()
        print(x,y,e)
        v_x = vantoc(x)
        v_y = vantoc(y)
        v_e = 0
        if e > 0.1:
            v_e = 0.1
        if e < -0.1:
            v_e -0.1
        print(v_x,v_y,v_e)
        Nao_move.Nao_tienThang(v_x,v_y,v_e)
        time.sleep(5)

thread_xla = threading.Thread(target=detect_nao)
thread_dk = threading.Thread(target=control_nao)

thread_xla.start()
time.sleep(1)
thread_dk.start()

thread_xla.join()
thread_dk.join()


print("ALL Task Completed!")