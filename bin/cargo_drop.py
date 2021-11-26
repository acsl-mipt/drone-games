#!/usr/bin/env python3
# coding=utf8

import rospy
import argparse
import airsim
import time
import math

from pathlib import Path
from airsim.types import Vector3r

import formations_gen as fgen

from std_msgs.msg import String

freq = 10

# преобразование дельты gps в дельту xyz по простейшей формуле (из интернета)
def enu_vector(g1, g2):
    n = g2[0] - g1[0]
    e = g2[1] - g1[1]
    u = g2[2] - g1[2]

    refLat = (g1[0]+g2[0])/2

    nm = n * 333400 / 3  # deltaNorth * 40008000 / 360
    em = e * 1001879 * math.cos(math.radians(refLat)) / 9  # deltaEast * 40075160 *cos(refLatitude) / 360

    return [em, nm, u]

def loop():
  global args

  """
  Формат строки публикуемой в топик, значения разделены пробелами:
  ВРЕМЯ_СЕК ШИРОТА_1 ДОЛГОТА_1 ВЫСОТА_1 ШИРОТА_2 ДОЛГОТА_2 ВЫСОТА_2 ... ШИРОТА_N ДОЛГОТА_N ВЫСОТА_N
  где ВРЕМЯ_СЕК - время выдачи, в секундах, ШИРОТА_N ДОЛГОТА_N ВЫСОТА_N - глобальные координаты N точки назначения.
  """
  pub = rospy.Publisher("~point", String, queue_size=10)

  rate = rospy.Rate(freq)

  l0 = len(p0)
  to_publish = l0*[False]
  s = ""
  pub_n = 0

  while not rospy.is_shutdown():
    if pub_n<l0:
      for n in range(1,args.num+1):
        m = args.model + str(n)
        p = client.simGetObjectPose(m).position
        if not p.containsNan():
          for i in range(l0):
            if not to_publish[i] and p.distance_to(p0[i]) < distance:
              to_publish[i] = True
              s += " " + g_str[i]
              pub_n += 1

    pub.publish(f"{time.time()}{s}")

    rate.sleep()

def arguments():
  global args, p0, g_str, distance

  parser = argparse.ArgumentParser()

  parser.add_argument("model", help="model name")
  parser.add_argument("num", type=int, help="models number")

  parser.add_argument("gps_points", type=Path, help="file with GPS coordinates of points")
  parser.add_argument("distance", type=Path, help="file with distance to start publishing point")

  parser.add_argument("--gps_ref", type=float, nargs=3, help="GPS reference point, center of local coordinate system")

  args = parser.parse_args()

  distance = fgen.read_values("distance", args.distance, 1, row_num = 1)[0][0]

  p0 = []
  g_str = []
  for g in fgen.read_values("gps_points", args.gps_points, 3):
    g_str.append(' '.join(map(str,g)))

    enu0 = enu_vector(args.gps_ref, g)

    p0.append(Vector3r(enu0[1], enu0[0], -enu0[2])) #ned

if __name__ == '__main__':
  global client

  client = airsim.MultirotorClient()
  client.confirmConnection()

  arguments()

  rospy.init_node("cargo_drop")

  try:
    loop()
  except rospy.ROSInterruptException:
    pass

  rospy.spin()
