#!/usr/bin/env python3
# coding=utf8

import rospy
import argparse
import math

from pathlib import Path

from std_msgs.msg import String
from gazebo_msgs.msg import ModelStates

import formations_gen as fgen

freq = 5
walls = {}

def arguments():
  global args, borders, centrals, brd_i

  parser = argparse.ArgumentParser()
  parser.add_argument("model", help="model name")
  parser.add_argument("num", type=int, help="models number")

  """
  Каждая строка файла центральных линий содержит координаты произвольного количества 3D точек, разделенных пробелами:
  x1 y1 z1 x2 y2 z2 ... xN yN zN
  Каждая центральная линия должна упираться в стену с окнами, последняя - в глухую стену.
  """
  parser.add_argument("centrals", type=Path, help="file with centrals")

  """
  Каталог с файлами стен, каждый файл с произвольным именем содержит строки из 4 чисел, разделенных пробелами.
  Каждая строка содержит относительные координаты центра окна (от конечной точки центральной линии) и размеры этого окна в системе отсчета Право-Верх,если смотреть по ходу движения
  x y w h
  """
  parser.add_argument("walls", type=Path, help="directory with walls files")

  """
  Ширина границы, пересекаемую аппаратами, которая ортогональна конечному отрезку центральной линии и проходит через её конечную точку
  """
  parser.add_argument("width", type=float, help="width of wall (border)")

  """
  Имена стен (имя файла стены без расширения), соответствующие окончаниям центральных линий в количестве на одну меньше (глухая стена не описыается), чем центральных линий
  """
  parser.add_argument("names", nargs='+', help="walls names for sequence")

  args = parser.parse_args()
  fgen.args = args

  centrals = fgen.read_values("centrals", args.centrals, 3, num_blocks = 2)
  if len(centrals) != len(args.names) + 1:
    print("number of centrals must be equal to number of names plus one")
    exit()

  borders = borders_from_centrals(centrals, args.width)
  brd_i = 0

  for i in range(len(centrals)):
    centrals[i] = ' '.join(map(str,centrals[i]))

  load_dir_files(args.walls, 4, walls, args.names)

def load_dir_files(dir_p, num_in_row, data_dict, names):
  for fp in dir_p.iterdir():
    vs = fgen.read_values(fp.name, fp, num_in_row)
    for i in range(len(vs)):
      vs[i] = ' '.join(map(str,vs[i]))

    n = fp.name.split('.')[0]
    data_dict[n] = ' '.join(vs)

  if len(data_dict) == 0:
    print("no data files in directory")
    exit()

  if names:
    for n in names:
      if n not in data_dict:
        print("no such name")
        exit()

def borders_from_centrals(cs, width):
  bs = []
  for c in cs:
    i = len(c) - 6
    cv = (c[i+3]-c[i+0], c[i+4]-c[i+1])
    len_cv = math.sqrt(cv[0]*cv[0] + cv[1]*cv[1])
    orto_cv = (-cv[1], cv[0])

    brd = [0, 0, 0, 0]
    for j in range(2):
      d = (orto_cv[j]*width)/(len_cv*2)
      brd[j] = c[j+i+3] + d
      brd[j+2] = c[j+i+3] - d

    bs.append(brd)

  return bs

def check_intersection(a, b, m):
  global brd_i

  res = False
  if brd_i < len(borders):
    brd = borders[brd_i]
    c = (brd[0], brd[1])
    d = (brd[2], brd[3])
    if fgen.intersect_on_dir(a, b, c, d):
      brd_i+=1

      #print(f"{m} intersected {brd}")
      res = True

  return res

def loop():
  global args

  pub={}
  """
  Формат строки для публикации в топик, значения разделены пробелами
  central:
  НОМЕР_СООБЩЕНИЯ ИМЯ_СТЕНЫ x1 y1 z1 x2 y2 z2 ... xN yN zN

  Имя означает стену, на которой заканчивается эта центральная линия.

  walls:
  НОМЕР_СООБЩЕНИЯ ИМЯ_СТЕНЫ x1 y1 w1 h1 x2 y2 w2 h2 ... xN yN wN hN

  Если центральная линия последняя, в central вместо имени используется символ '|', а в walls ничего не публикуется.
  """
  for n in ("central", "walls"):
    pub[n] = rospy.Publisher("~" + n, String, queue_size=10)

  prev_plane_pos = {}
  i = 1

  rate = rospy.Rate(freq)
  while not rospy.is_shutdown():
    for n in range(1,args.num+1):
      m = args.model + str(n)
      if m in fgen.plane_pos:
        if m in prev_plane_pos:
          to_next_brd = check_intersection(prev_plane_pos[m], fgen.plane_pos[m], m)
        else:
          to_next_brd = False
        prev_plane_pos[m] = fgen.plane_pos[m]

        if to_next_brd:
          break

    if brd_i < len(borders):
      if brd_i < len(args.names):
        p_name = args.names[brd_i]
        pub['walls'].publish(str(i) + ' ' + p_name + ' ' + walls[p_name])
      else:
        p_name = '|'

      pub['central'].publish(str(i) + ' ' + p_name + ' ' + centrals[brd_i])
      i+=1

    rate.sleep()

if __name__ == '__main__':
  arguments()

  rospy.init_node("path_generator")

  rospy.Subscriber("/gazebo/model_states", ModelStates, fgen.model_states)

  try:
    loop()
  except rospy.ROSInterruptException:
    pass

  rospy.spin()
