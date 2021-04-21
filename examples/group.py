#!/usr/bin/env python3
# coding=utf8

import rospy
import time
import sys
import math

from sensor_msgs.msg import NavSatFix
from geometry_msgs.msg import TwistStamped, PoseStamped
from mavros_msgs.msg import PositionTarget, State, ExtendedState
from geographic_msgs.msg import GeoPointStamped

from mavros_msgs.srv import SetMode, CommandBool, CommandVtolTransition, CommandHome

instances_num = 3 #количество аппаратов
freq = 20 #Герц, частота посылки управляющих команд аппарату
node_name = "offboard_node"
data = {}
lz = {}

def subscribe_on_mavros_topics(suff, data_class):
  #подписываемся на Mavros топики всех аппаратов
  for n in range(1, instances_num + 1):
    data[n] = {}
    topic = f"/mavros{n}/{suff}"
    rospy.Subscriber(topic, data_class, topic_cb, callback_args = (n, suff))

def topic_cb(msg, callback_args):
  n, suff = callback_args
  data[n][suff] = msg

def service_proxy(n, path, arg_type, *args, **kwds):
  service = rospy.ServiceProxy(f"/mavros{n}/{path}", arg_type)
  ret = service(*args, **kwds)

  rospy.loginfo(f"{n}: {path} {args}, {kwds} => {ret}")

def arming(n, to_arm):
  d = data[n].get("state")
  if d is not None and d.armed != to_arm:
    service_proxy(n, "cmd/arming", CommandBool, to_arm)

def set_mode(n, new_mode):
  d = data[n].get("state")
  if d is not None and d.mode != new_mode:
    service_proxy(n, "set_mode", SetMode, custom_mode=new_mode)

def vtol_to_fw(n):
  d = data[n].get("extended_state")
  if d is not None:
    if d.vtol_state != ExtendedState.VTOL_STATE_FW and d.vtol_state != ExtendedState.VTOL_STATE_TRANSITION_TO_FW:
      service_proxy(n, "cmd/vtol_transition", CommandVtolTransition, state = ExtendedState.VTOL_STATE_FW)

def subscribe_on_topics():
  # глобальная (GPS) система координат
  subscribe_on_mavros_topics("global_position/global", NavSatFix)

  #локальная система координат, точка отсчета = место включения аппарата
  subscribe_on_mavros_topics("local_position/pose", PoseStamped)
  subscribe_on_mavros_topics("local_position/velocity_local", TwistStamped)

  #состояние
  subscribe_on_mavros_topics("state", State)
  subscribe_on_mavros_topics("extended_state", ExtendedState)


def on_shutdown_cb():
  rospy.logfatal("shutdown")

#ROS/Mavros работают в системе координат ENU(Восток-Север-Вверх), автопилот px4 и протокол сообщений Mavlink используют систему координат NED(Север-Восток-Вниз)
#см. также описание mavlink сообщения https://mavlink.io/en/messages/common.html#SET_POSITION_TARGET_LOCAL_NED

#Управление по точкам, локальная система координат.
def set_pos(pt, x, y, z):
  pt.type_mask = pt.IGNORE_VX | pt.IGNORE_VY | pt.IGNORE_VZ | pt.IGNORE_AFX | pt.IGNORE_AFY | pt.IGNORE_AFZ | pt.IGNORE_YAW | pt.IGNORE_YAW_RATE

  #Смещение на восток
  pt.position.x = x
  #Смещение на север
  pt.position.y = y
  #Высота, направление вверх
  pt.position.z = z

#Управление по скоростям, локальная система координат, направления совпадают с оными в глобальной системе координат
def set_vel(pt, vx, vy, vz):
  pt.type_mask = pt.IGNORE_PX | pt.IGNORE_PY | pt.IGNORE_PZ | pt.IGNORE_AFX | pt.IGNORE_AFY | pt.IGNORE_AFZ | pt.IGNORE_YAW | pt.IGNORE_YAW_RATE

  #Скорость, направление на восток
  pt.velocity.x = vx
  #Скорость, направление на север
  pt.velocity.y = vy
  #Скорость, направление вверх
  pt.velocity.z = vz

#Управление по vx, vy, pz, локальная система координат.
def set_vxy_pz(pt, vx, vy, pz):
  # Не игнорируем vz, из за особенностей работы автопилота px4.
  pt.type_mask = pt.IGNORE_PX | pt.IGNORE_PY | pt.IGNORE_AFX | pt.IGNORE_AFY | pt.IGNORE_AFZ | pt.IGNORE_YAW | pt.IGNORE_YAW_RATE

  #обнуляем, но не используем в управлении
  pt.velocity.z = 0

  #Скорость, направление на восток
  pt.velocity.x = vx
  #Скорость, направление на север
  pt.velocity.y = vy
  #Высота, направление вверх
  pt.position.z = pz

#взлет коптера
def mc_takeoff(pt, n, dt):
  if dt<10:
    #скорость вверх
    set_vel(pt, 0, 0, 4)

    #армимся и взлетаем с заданной скоростью
    if dt>5:
      arming(n, True)

#пример управления коптерами
def mc_example(pt, n, dt):
  mc_takeoff(pt, n, dt)

  if dt>10 and dt<15:
    #скорость вверх
    set_vel(pt, 0, 0, 1)

  #летим в одном направлении, разносим по высоте
  if dt>15 and dt<20:
    set_vel(pt, 5, 0, (n-2)/2)

  #первый коптер летит по квадрату, остальные следуют с такой же горизонтальнй скоростью как первый
  if dt>20 and dt<30:
    if n == 1:
      if dt>20:
        set_vel(pt, 0, -5, 0)

      if dt>24:
        set_vel(pt, -5, 0, 0)

      if dt>27:
        set_vel(pt, 0, 5, 0)
    else:
      v1 = data[1]["local_position/velocity_local"].twist.linear
      set_vel(pt, v1.x, v1.y, 0)

  #направляем каждого в свою точку
  if dt>30 and dt<35:
    set_pos(pt, 0, (n-2)*3, 10)

  #снижаем на землю
  if dt>35:
    set_vel(pt, 0, 0, -1)

#пример управления vtol
def vtol_example(pt, n, dt):
  mc_takeoff(pt, n, dt)

  #летим вперед-влево с разными скоростями медленно в режиме коптера
  if dt>15 and dt<20:
    set_vel(pt, 5, n, 0)

  #запоминаем высоту, на которую прилетели в режиме коптера
  if dt>19 and dt<20:
    lz[n] = data[n]["local_position/pose"].pose.position.z

  #переходим в самолетный режим, летим быстрее с одинаковой скоростью
  if dt>20 and dt<25:
    vtol_to_fw(n)
    set_vxy_pz(pt, 15, 0, lz[n])

  if dt>25 and dt<30:
    #1-ый на юг
    if n == 1:
      set_vxy_pz(pt, 0, -15, lz[n])

    #2-ой чуть снижаем
    if n == 2:
      set_vxy_pz(pt, 15, 0, lz[n]-10)

    #3-ий на север
    if n == 3:
      set_vxy_pz(pt, 0, 15, lz[n])

  #всех направляем в одну точку, но с разными высотами
  #в самолетном режиме, ожидает вокруг точки назначения
  if dt>30:
    set_pos(pt, 0, 0, n*10)

def offboard_loop(mode):
  pub_pt = {}
  #создаем топики, для публикации управляющих значений
  for n in range(1, instances_num + 1):
    pub_pt[n] = rospy.Publisher(f"/mavros{n}/setpoint_raw/local", PositionTarget, queue_size=10)

  pt = PositionTarget()
  #см. также описание mavlink сообщения https://mavlink.io/en/messages/common.html#SET_POSITION_TARGET_LOCAL_NED
  pt.coordinate_frame = pt.FRAME_LOCAL_NED

  t0 = time.time()

  #цикл управления
  rate = rospy.Rate(freq)
  while not rospy.is_shutdown():
    dt = time.time() - t0

    #управляем каждым аппаратом централизованно
    for n in range(1, instances_num + 1):
      set_mode(n, "OFFBOARD")

      if mode == 0:
        mc_example(pt, n, dt)
      elif mode == 1:
        vtol_example(pt, n, dt)

      pub_pt[n].publish(pt)

    rate.sleep()

if __name__ == '__main__':
  rospy.init_node(node_name)
  rospy.loginfo(node_name + " started")

  subscribe_on_topics()

  rospy.on_shutdown(on_shutdown_cb)

  m = 0

  if len(sys.argv) > 1:
    arg = sys.argv[1]
    if arg == "vtol":
      m = 1

  try:
    offboard_loop(m)
  except rospy.ROSInterruptException:
    pass

  rospy.spin()
