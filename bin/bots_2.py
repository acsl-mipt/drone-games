#!/usr/bin/env python3
# coding=utf8

import airsim
import os
import time
import numpy as np
from PIL import Image, ImageOps
import multiprocessing.dummy as mp


# connect to the AirSim simulator
client = airsim.MultirotorClient()
client.confirmConnection()



# set first group params
N_1 = 6
VELOCITY = 7
T_SLEEP_SNAKE = 1.5
T_BETWEEN_GROUPS = 4
WAIT_FOR_LANDING = 5
FOLLOW_NAME = 'iris1'
BOT_NAME = 'zbot'
DZ_VAL = -5

# set second group params
N_2 = 6
DELTA_X, DELTA_Y, DELTA_Z = 0.95, 0.95, 0.95
K = 1.5

###
N_3, N_4, N_5 = 0, 0, 0
LOOP_N = 3

X_0, Y_0, Z_0 = 450, 100, 101.6 + 2.337

time.sleep(WAIT_FOR_LANDING)

start_Z = client.simGetVehiclePose(FOLLOW_NAME).position.z_val

# set route
route_X = [440, 320, 400, 430, 510, 540, 520, 500, 480, 460, 490, 530, 560, 520]
route_Y = [170,  10, -50, -10, -70, -30, -15,   0,  15,  30,  70,  40,  80, 110]
route_Z = [130, 120, 115, 125, 115, 120, 125, 110, 130, 115, 110, 115, 131, 120]

# [520, 560, 530, 490, 460, 480, 500, 520, 540, 510, 430, 400, 320, 440, 520]
# [110,  80,  40,  70,  30,  15,   0, -15, -30, -70, -10, -50,  10, 170, 110]
# [120, 131, 115, 110, 115, 130, 110, 125, 120, 115, 125, 115, 120, 130, 120]


def create_path_snake(i):
    path = []
    for _ in range(LOOP_N):
        for x, y, z in zip(route_X, route_Y, route_Z):
            path.append(airsim.Vector3r(x - i * 2 - X_0, y - Y_0, -z + Z_0))
    return path

def create_path_heap(i, n_1, n_2):  # unused n_2

    path = []
    for _ in range(LOOP_N):
        for x, y, z in zip(route_X, route_Y, route_Z):
            x_0 = X_0 + DELTA_X if i == n_1 else X_0 - DELTA_X if i == n_1 + 6 else X_0
            y_0 = Y_0 + DELTA_Y if i == n_1 + 1 else Y_0 - DELTA_Y if i == n_1 + 2 else Y_0
            z_0 = Z_0 - DELTA_Z if i == n_1 + 3 else Z_0 + DELTA_Z if i == n_1 + 4 else Z_0

            path.append(airsim.Vector3r(x - i * 2 - x_0, y - y_0, -z + z_0))
    return path


nums = list(range(N_1))
names = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))
POSES_0 = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))

# enable first group
di = {}
for i, n in zip(nums, names):
    client.enableApiControl(True, n)
    client.armDisarm(True, n)
    di[i] = client.takeoffAsync(1, vehicle_name=n)
for i in nums:
    di[i].join()

#while client.simGetVehiclePose(FOLLOW_NAME).position.z_val > start_Z + DZ_VAL:
#    time.sleep(0.5)

# move first group
di = {}
for i in range(0, N_1):
    client.moveOnPathAsync(create_path_snake(i), velocity=VELOCITY, vehicle_name='{}_{}'.format(BOT_NAME, i + 1))
    time.sleep(T_SLEEP_SNAKE)


time.sleep(T_BETWEEN_GROUPS)


nums = list(range(N_1, N_1 + N_2))
names = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))
POSES_0 = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))

# enable second group
di = {}
for i, n in zip(nums, names):
    client.enableApiControl(True, n)
    client.armDisarm(True, n)
    di[i] = client.takeoffAsync(1, vehicle_name=n)
for i in nums:
    di[i].join()

# move second group
for i in reversed(range(N_1, N_1 + N_2)):
    client.moveOnPathAsync(create_path_heap(i, N_1, N_1 + N_2), velocity=VELOCITY, vehicle_name='{}_{}'.format(BOT_NAME, i + 1))

###################
"""
time.sleep(T_BETWEEN_GROUPS)


nums = list(range(N_1 + N_2, N_1 + N_2 + N_3))
names = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))
POSES_0 = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))

# enable second group
di = {}
for i, n in zip(nums, names):
    client.enableApiControl(True, n)
    client.armDisarm(True, n)
    di[i] = client.takeoffAsync(1, vehicle_name=n)
for i in nums:
    di[i].join()

# move second group
for i in range(N_1 + N_2, N_1 + N_2 + N_3):
    client.moveOnPathAsync(create_path_snake(i), velocity=VELOCITY, vehicle_name='{}_{}'.format(BOT_NAME, i + 1))
    time.sleep(T_SLEEP_SNAKE)


time.sleep(T_BETWEEN_GROUPS)


nums = list(range(N_1 + N_2 + N_3, N_1 + N_2 + N_3 + N_4))
names = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))
POSES_0 = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))

# enable second group
di = {}
for i, n in zip(nums, names):
    client.enableApiControl(True, n)
    client.armDisarm(True, n)
    di[i] = client.takeoffAsync(1, vehicle_name=n)
for i in nums:
    di[i].join()

# move second group
for i in reversed(range(N_1 + N_2 + N_3, N_1 + N_2 + N_3 + N_4)):
    client.moveOnPathAsync(create_path_heap(i, N_1 + N_2 + N_3, N_1 + N_2 + N_3 + N_4), velocity=VELOCITY, vehicle_name='{}_{}'.format(BOT_NAME, i + 1))


time.sleep(T_BETWEEN_GROUPS)


nums = list(range(N_1 + N_2 + N_3 + N_4, N_1 + N_2 + N_3 + N_4 + N_5))
names = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))
POSES_0 = list(map(lambda x: "{}_{}".format(BOT_NAME, x + 1), nums))

# enable second group
di = {}
for i, n in zip(nums, names):
    client.enableApiControl(True, n)
    client.armDisarm(True, n)
    di[i] = client.takeoffAsync(1, vehicle_name=n)
for i in nums:
    di[i].join()

# move second group
for i in range(N_1 + N_2 + N_3 + N_4, N_1 + N_2 + N_3 + N_4 + N_5):
    client.moveOnPathAsync(create_path_snake(i), velocity=VELOCITY, vehicle_name='{}_{}'.format(BOT_NAME, i + 1))
    time.sleep(T_SLEEP_SNAKE)
"""

