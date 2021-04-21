#!/usr/bin/env python3
# coding=utf8

import rospy
import argparse
import random

from pathlib import Path

from std_msgs.msg import String
from gazebo_msgs.msg import ModelStates

freq = 5
fs_num = 4
plane_pos={}
formations = {}
finish_name = '|'

def arguments():
  global args, borders, brd_i

  parser = argparse.ArgumentParser()
  parser.add_argument("model", help="model name")
  parser.add_argument("num", type=int, help="models number")

  """
  Файл с границами содержит пары координат отрезков в плоскости XY в виде 4 чисел в каждой строке, разделенных пробелами:
  ax ay bx by
  ...
  Граница считается пересеченной, если аппарат пересекает отрезок AB справа налево, если смотреть по направлению из A в B.
  """
  parser.add_argument("borders", type=Path, help="file with borders")

  """
  Каталог с файлами формаций, каждый файл с произвольным именем содержит строки из 3 чисел, разделенных пробелами.
  Каждая строка обозначает относительные координаты аппарата в системе отсчета Право-Вперед-Вверх,
    где Вперед - направление движения группы.

  x1 y1 z1
  x2 y2 z2
  ...
  """
  parser.add_argument("formations", type=Path, help="directory with formation files")
  parser.add_argument("--names", nargs=fs_num, help="formations names for sequence")

  args = parser.parse_args()

  borders = read_values("borders", args.borders, 4)
  brd_i = 0

  for fp in args.formations.iterdir():
    fs = read_values(fp.name, fp, 3, args.num)
    for i in range(len(fs)):
      fs[i] = ' '.join(map(str,fs[i]))

    n = fp.name.split('.')[0]
    formations[n] = ' '.join(fs)


  if len(formations) == 0:
    print("no formations")
    exit()

  if args.names:
    for n in args.names:
      if n not in formations:
        print("no such name in formations")
        exit()

  choose_formation(True)

def read_values(name, fp, num = None, row_num = None, num_blocks = 1):
  vs = []
  with fp.open() as f:
    for l in f.readlines():
      l = l.strip()
      if len(l) == 0:
        continue

      values = l.split()
      v_len = len(values)
      d = v_len//num
      o = v_len%num

      if d < num_blocks or o != 0:
        print("invalid " + name)
        exit()

      vs.append(list(map(float,values)))

  if len(vs) == 0:
    print("empty " + name)
    exit()

  if row_num is not None:
    if len(vs) != row_num:
      print("invalid number of rows in " + name)
      exit()

  return vs

def model_states(msg):
  global args

  for i in range(len(msg.name)):
    n = msg.name[i]
    if n.startswith(args.model):
      p = msg.pose[i].position
      plane_pos[n] = (p.x, p.y)

def area(a, b, c):
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

def inter(a, b, c, d):
  if a > b:
    a,b = b,a

  if c > d:
    c,d = d,c

  return max(a,c) <= min(b,d)

def intersect_on_dir(a, b, c, d):
  if inter(a[0], b[0], c[0], d[0]) and inter(a[1], b[1], c[1], d[1]):
    a = (area(a,b,c), area(a,b,d), area(c,d,a), area(c,d,b))
    if a[0] >= 0 and a[1] <= 0 and a[2] <= 0 and a[3] >= 0:
      return True

  return False

def choose_formation(init = False):
  global f_name, f_i

  if init:
    f_i = 0
  else:
    f_i += 1

  if f_i < fs_num:
    if args.names:
      f_name = args.names[f_i]
    else:
      f_name = random.choice(list(formations))
  elif f_i == fs_num:
    f_name = finish_name
  else:
    f_name = None

def check_intersection(a, b, m):
  global brd_i

  brd = borders[brd_i]
  c = (brd[0], brd[1])
  d = (brd[2], brd[3])
  if intersect_on_dir(a, b, c, d):
    brd_i+=1
    if brd_i >= len(borders):
      brd_i = 0

    choose_formation()
    print(f"{m} intersected {brd}, next border: {borders[brd_i]}")

    res = True
  else:
    res = False

  return res


def loop():
  global args, f_name

  """
  Формат строки для публикации в топик: "номер_сообщения имя_формации x1 y1 z1 x2 y2 z2 ... xN yN zN"
  если финишная граница пересечена, формат строки со спец символом: "номер_сообщения |"
  """
  pub_f = rospy.Publisher("~formation", String, queue_size=10)
  prev_plane_pos = {}
  i = 1

  rate = rospy.Rate(freq)
  while not rospy.is_shutdown():
    for n in range(1,args.num+1):
      m = args.model + str(n)
      if m in plane_pos:
        if m in prev_plane_pos:
          to_next_brd = check_intersection(prev_plane_pos[m], plane_pos[m], m)
        else:
          to_next_brd = False
        prev_plane_pos[m] = plane_pos[m]

        if to_next_brd:
          break

    if f_name is not None:
      if f_name == finish_name:
        suf = ''
      else:
        suf = ' ' + formations[f_name]

      pub_f.publish(str(i) + ' ' + f_name + suf)
      i+=1

    rate.sleep()

def on_shutdown_cb():
  pass

if __name__ == '__main__':
  random.seed()

  arguments()

  rospy.init_node("formations_generator")

  rospy.Subscriber("/gazebo/model_states", ModelStates, model_states)

  rospy.on_shutdown(on_shutdown_cb)

  try:
    loop()
  except rospy.ROSInterruptException:
    pass

  rospy.spin()
