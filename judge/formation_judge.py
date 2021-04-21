#!/usr/bin/env python3
# coding=utf8

# import atexit
# from statistics import median
# import pickle
import argparse
import csv
from pathlib import Path
from subprocess import Popen
from time import monotonic

import numpy as np
import rospy
from gazebo_msgs.msg import ModelStates, ContactsState
from scipy.spatial import KDTree
from scipy.spatial.transform import Rotation
from sklearn.preprocessing import normalize
from std_msgs.msg import String

import warnings
warnings.filterwarnings('ignore')

# PARAMETERS
COLLISION_DELTA_TIME = 0.5
# BEST_FORMATION_TICKS = 30
REFORMATION_THRESHOLD = 2
A, B, C = 10, 0.5, 3
SPEED_THRESHOLD = 5

# PASS_N = 3
# MODEL = 'iris'
# NUM = 6
MODEL = None
NUM = None
MAX_SPEED = 12
FILENAME = 'formation'

ZONE_BORDERS = [[31, -62, 52, -62],
                [31, 62, 52, 62],
                [-31, 62, -52, 62],
                [-31, -62, -52, -62]]
# ZONE_BORDERS = [[0, -62, 100, -62],
#                [0, 62, 100, 62],
#                [0, 62, -100, 62],
#                [0, -62, -100, -62]]
INSIDE_SQUARE = [-32, -63, 32, 63]
OUTSIDE_SQUARE = [-53, -83, 53, 83]
REFORMATION_SQUARES = [[-52, -82, 52, -62], [-52, 62, 52, 82]]
# FIXME
#REFORMATION_SQUARES = [[-250, -400, 250, -62], [-250, 62, 250, 400]]
FINISH_NAME = '|'

plane_poses = {}
brd_i = 0
distances = []
side_timer, side_intruder, side_time = None, {}, 0
all_timer, all_time = None, 0
reformation_timer, reformation_times = None, []
efficiency_distance, efficiency_distances = 0, []
global_counter = 0
FORMATION = None
formation_zone = False
is_formation_changed = False
collisions_amount = 0
last_collision_time = None
finished = False
finishing = False
mean_squared_deviations = []
print_once = True
prev_poses = None

# update
collisions_pub, side_time_pub, msd_current_pub, msd_overall_pub = None, None, None, None
reformation_pub, final_pub = None, None
parser_args = None


class FormationJudge:
    def __init__(self, model, num, counter) -> None:
        super().__init__()

        Popen(["/opt/ros/noetic/bin/rosrun", "topic_tools", "throttle", "messages",
               "/gazebo/model_states", "20", "/gazebo/model_states_throttled"], shell=False)

        set_model(model)
        set_num(num)
        set_filename(counter)
        # set_updaters(cu)

        rospy.init_node("formation_judge")
        rospy.on_shutdown(on_shutdown_cb)
        # atexit.register(exit_handler)

        subscribe()
        init_publishers()

        try:
            main_loop()
        except rospy.ROSInterruptException:
            pass

        rospy.spin()


# def set_updaters(collision):
#     global collision_updater
#     collision_updater = collision


def set_model(model):
    global MODEL
    MODEL = model


def set_num(num):
    global NUM
    NUM = num


def set_filename(counter):
    global FILENAME
    FILENAME = FILENAME + str(counter)


# noinspection PyUnresolvedReferences,PyTypeChecker
def main_loop():
    global formation_zone, side_timer, side_intruder, side_time, is_formation_changed, print_once

    rate = rospy.Rate(20)

    prev_plane_pos = {}

    while not rospy.is_shutdown():
        for n in range(1, NUM + 1):
            m = MODEL + str(n)
            if m in plane_poses:
                if m in prev_plane_pos:
                    a, b = prev_plane_pos[m], plane_poses[m]
                    to_next_brd = check_zone_intersection(a, b)
                else:
                    to_next_brd = False
                prev_plane_pos[m] = plane_poses[m]

                side_intruder[m] = not is_inside_zone(plane_poses[m])

                if to_next_brd:
                    formation_zone = not formation_zone
                    is_formation_changed = True
                    break

        if any(side_intruder.values()) and side_timer is None:
            # print(side_intruder)
            side_timer = monotonic()
        elif (not any(side_intruder.values()) or finished) and side_timer is not None:
            side_time += monotonic() - side_timer
            side_time_pub.publish(str(side_time))
            side_timer = None
            write_all()

        if finished and print_once:
            final_print()
            print_once = False
            write_all()

        rate.sleep()


def final_print(w=False):
    global print_once, all_time, side_time, mean_squared_deviations

    # if all_time == 0:
    if all_timer is not None:
        # noinspection PyTypeChecker
        all_time = monotonic() - all_timer

    if side_timer is not None:
        # noinspection PyTypeChecker
        side_time += monotonic() - side_timer
        # side_time_pub.publish(str(side_time))
        # write_all()

    final_score = all_time + A * collisions_amount + B * side_time + C * sum(mean_squared_deviations)
    speed_score = all_time + A * collisions_amount + B * side_time + C * np.sqrt(
        np.mean(np.array(list(map(lambda x: 0 if x < SPEED_THRESHOLD else x, mean_squared_deviations)))))
    efficiency_score = np.mean(reformation_times) + np.mean(efficiency_distances)

    if not w:
        print("TIME:                    {} \n"
              "MEAN SQUARED DEVIATIONS: {} \n"
              "COLLISIONS:              {} \n"
              "REFORMATION TIMES:       {} \n"
              "SIDE TIME:               {} \n"
              "___________________________ \n"
              "FINAL SCORE:             {} \n"
              "___________________________ \n"
              "NOMINATIONS                 \n"
              "SYNCHRONICITY:           {} \n"
              "EFFICIENCY:              {} \n"
              "SPEED:                   {}".format(all_time,
                                                   mean_squared_deviations,
                                                   collisions_amount,
                                                   reformation_times,
                                                   side_time,
                                                   final_score,
                                                   sum(mean_squared_deviations),
                                                   efficiency_score,
                                                   speed_score))
        string = "::".join(list(map(str, [np.round(final_score), np.round(sum(mean_squared_deviations), 2),
                                          np.round(efficiency_score, 2), np.round(speed_score, 2)])))
        # noinspection PyUnresolvedReferences
        final_pub.publish(string)

    return all_time, mean_squared_deviations, collisions_amount, reformation_times, side_time, final_score, sum(
        mean_squared_deviations), efficiency_score, speed_score


def subscribe():
    rospy.Subscriber("/gazebo/model_states_throttled", ModelStates, _gz_states_cb)
    rospy.Subscriber("/formations_generator/formation", String, _formation_cb)
    rospy.Subscriber("/bumper_states", ContactsState, _collision_cb)  # /states[0]/info


def init_publishers():
    global collisions_pub, side_time_pub, msd_current_pub, msd_overall_pub, reformation_pub, final_pub
    collisions_pub = rospy.Publisher('/collisions', String, queue_size=10)
    side_time_pub = rospy.Publisher('/side_time', String, queue_size=10)
    msd_current_pub = rospy.Publisher('/msd_current', String, queue_size=10)
    msd_overall_pub = rospy.Publisher('/msd_overall', String, queue_size=10)
    reformation_pub = rospy.Publisher('/reformation', String, queue_size=10)
    final_pub = rospy.Publisher('/final', String, queue_size=10)


def _formation_cb(_formation):
    global FORMATION, finishing, all_timer, reformation_timer

    if all_timer is None:
        all_timer = monotonic()
        reformation_timer = monotonic()

    if _formation.data.split()[1] == FINISH_NAME:
        finishing = True
    else:
        formation_str = iter(list(map(float, _formation.data.split()[2:])))
        formation = []
        for x, y, z in zip(formation_str, formation_str, formation_str):
            formation.append([x, y, z])
        formation = np.array(formation)
        FORMATION = mean_p(formation)  # bary_form


# noinspection PyUnresolvedReferences
def _collision_cb(_contacts):
    global last_collision_time, collisions_amount

    for state in _contacts.states:
        collision_1_name = state.collision1_name.split('::')[0]
        collision_2_name = state.collision2_name.split('::')[0]
        if collision_1_name.startswith(MODEL) and collision_2_name.startswith(MODEL):
            if last_collision_time is None:
                collisions_amount += 1
                last_collision_time = monotonic()
                collisions_pub.publish(str(collisions_amount))
                # collision_updater(collisions_amount)
                write_all()
            elif monotonic() - last_collision_time > COLLISION_DELTA_TIME:
                collisions_amount += 1
                last_collision_time = monotonic()
                collisions_pub.publish(str(collisions_amount))
                # collision_updater(collisions_amount)
                write_all()
            # print(collisions_amount)


def _gz_states_cb(_states):
    global FORMATION, distances, global_counter, all_timer, all_time, finished, mean_squared_deviations, \
        reformation_timer, is_formation_changed, prev_poses, efficiency_distance, efficiency_distances

    poses = []
    twists = []
    x = y = z = 0  # c = 0

    for i in range(len(_states.name)):
        n = _states.name[i]
        if n.startswith(MODEL):
            pose = _states.pose[i].position
            poses.append([pose.x, pose.y, pose.z])
            x += pose.x
            y += pose.y
            z += pose.z
            # c += 1

            plane_poses[n] = (pose.x, pose.y)

            twist = _states.twist[i].linear
            twists.append([twist.x, twist.y, twist.z])

    # barycenter_coordinates = np.array([x / c, y / c, z / c])
    poses = np.array(poses)

    # if any(poses[:, 2] > 0.5) is True and all_timer is None:
    #     # print("ALL TIMER STARTED")
    #     # all_timer = monotonic()
    #     reformation_timer = monotonic()
    # if all(poses[:, 2] < 0.5) and all_timer is not None and monotonic() - all_timer > 60:

    if finishing and (all([is_finished_0(p) for p in poses]) or
                      all([is_finished_1(p) for p in poses])) and not finished:
        # print("ALL TIMER STOPPED")
        finished = True
        write_all(final=True)
        # noinspection PyTypeChecker
        # all_time = monotonic() - all_timer

    twists = np.array(twists)
    mean_twists = twists.mean(axis=0)
    r = Rotation.from_matrix(get_new_basis(mean_twists).T)
    rel_mean_poses = calculate_relative_positions(poses, r)

    if FORMATION is not None and formation_zone:
        # noinspection PyTypeChecker
        formation_copy = np.copy(FORMATION)
        f_tree = KDTree(formation_copy)
        distance = 0
        for pose in rel_mean_poses:
            d, idx = f_tree.query(pose)
            distance += d ** 2
            formation_copy = np.delete(formation_copy, idx, axis=0)
            f_tree = KDTree(formation_copy)
        distances.append(distance)
        # print("Current deviation = ", distance)
        # print("Current median deviation = ", median(distances))
        # noinspection PyUnresolvedReferences
        msd_current_pub.publish(str(np.sqrt(np.mean(distance))))

        if distance < REFORMATION_THRESHOLD and reformation_timer is not None:
            # print("REFORMATION TIME = ", monotonic() - reformation_timer)
            reformation_times.append(monotonic() - reformation_timer)
            # noinspection PyUnresolvedReferences,PyTypeChecker
            reformation_pub.publish(str(monotonic() - reformation_timer))
            reformation_timer = None
            write_all()

    elif distances:
        # print("Overall mean squared deviation = ", np.sqrt(np.mean(distances)))
        mean_squared_deviations.append(np.sqrt(np.mean(distances)))
        # noinspection PyUnresolvedReferences
        msd_overall_pub.publish(str(np.sqrt(np.mean(distances))))
        write_all()

        # with open('distances_{}.pickle'.format(global_counter), 'wb') as file:
        #     pickle.dump(distances, file)
        # global_counter += 1
        distances = []

        if len(reformation_times) != len(mean_squared_deviations):
            reformation_times.append(np.inf)
            write_all()

    if FORMATION is not None and not formation_zone:
        # noinspection PyTypeChecker
        formation_copy = np.copy(FORMATION)
        f_tree = KDTree(formation_copy)
        distance = 0
        for pose in rel_mean_poses:
            d, idx = f_tree.query(pose)
            distance += d ** 2
            formation_copy = np.delete(formation_copy, idx, axis=0)
            f_tree = KDTree(formation_copy)
        if distance > REFORMATION_THRESHOLD and (
                reformation_timer is None) and (
                all_timer is not None) and (
                is_formation_changed):
            # print("REFORMATION STARTED")
            reformation_timer = monotonic()
            is_formation_changed = False
        elif distance < REFORMATION_THRESHOLD and reformation_timer is not None:
            # print("REFORMATION TIME = ", monotonic() - reformation_timer)
            reformation_times.append(monotonic() - reformation_timer)
            # noinspection PyUnresolvedReferences,PyTypeChecker
            reformation_pub.publish(str(monotonic() - reformation_timer))
            reformation_timer = None
            write_all()

    if reformation_timer is not None and prev_poses is not None:
        efficiency_distance += sum(list(map(np.linalg.norm, poses - prev_poses)))
    elif efficiency_distance != 0:
        # noinspection PyTypeChecker
        efficiency_distances.append(efficiency_distance / NUM / MAX_SPEED)
        efficiency_distance = 0
        write_all()

    prev_poses = poses


# def summarize():
#     min_distances = []
#     for i in range(global_counter):
#         with open('distances_{}.pickle'.format(i), 'rb') as file:
#             data = pickle.load(file)
#             min_distances.append(min([sum(data[i:i + BEST_FORMATION_TICKS])
#                                       for i in range(len(data) - BEST_FORMATION_TICKS - 1)]))
#     return min_distances


def calculate_relative_positions(poses, r):
    return np.array(list(map(r.apply, mean_p(poses))))


def get_new_basis(twists):
    twists[2] = 0
    ey = normalize(twists[:, np.newaxis], axis=0).ravel()
    ez = np.array([0, 0, 1])
    return np.array([np.cross(ey, ez), ey, ez])


def mean_p(iterable):
    arr = []
    for it in iterable:
        arr.append(iterable - it)
    arr = np.array(arr)
    return np.round(np.mean(arr, axis=0), 2)


def check_zone_intersection(a, b):
    global brd_i

    brd = ZONE_BORDERS[brd_i]
    c = (brd[0], brd[1])
    d = (brd[2], brd[3])
    if intersect_on_dir(a, b, c, d):
        brd_i += 1
        if brd_i >= len(ZONE_BORDERS):
            brd_i = 0

        res = True
    else:
        res = False

    return res


def is_inside_zone(point):
    return is_inside_square(point, OUTSIDE_SQUARE) and not is_inside_square(point, INSIDE_SQUARE)


def is_finished_0(point):
    return is_inside_square(point, REFORMATION_SQUARES[0])


def is_finished_1(point):
    return is_inside_square(point, REFORMATION_SQUARES[1])


def is_inside_square(point, square):
    return square[0] < point[0] < square[2] and square[1] < point[1] < square[3]


def intersect_on_dir(a, b, c, d):
    if inter(a[0], b[0], c[0], d[0]) and inter(a[1], b[1], c[1], d[1]):
        a = (area(a, b, c), area(a, b, d), area(c, d, a), area(c, d, b))
        if a[0] >= 0 >= a[1] and a[2] <= 0 <= a[3]:
            return True
    return False


def area(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def inter(a, b, c, d):
    if a > b:
        a, b = b, a

    if c > d:
        c, d = d, c

    return max(a, c) <= min(b, d)


def on_shutdown_cb():
    final_print()
    write_all()


def write_all(final=False):
    names = ['all_time', 'mean_squared_deviations', 'collisions_amount', 'reformation_times', 'side_time',
             'final_score', 'sum(mean_squared_deviations)', 'efficiency_score', 'speed_score']
    line = ["FINAL"] if final else []
    for el, name in zip(final_print(w=True), names):
        line.append(name)
        line.append(el)
    mode = 'a' if Path(FILENAME).is_file() else 'w'
    with open(FILENAME, mode) as f:  # , newline=''
        wr = csv.writer(f, quoting=csv.QUOTE_ALL)
        wr.writerow(line)


def get_list_name(lst):
    try:
        for key, value in globals().items():
            if type(value) == list and value == lst:
                return key
    except RuntimeError:
        return get_list_name(lst)


# def exit_handler():
#     final_print()

def arguments():
    global parser_args

    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="model name")
    parser.add_argument("num", type=int, help="models number")
    parser.add_argument("counter", help="counter")

    parser_args = parser.parse_args()


if __name__ == '__main__':
    arguments()
    # noinspection PyUnresolvedReferences
    FormationJudge(parser_args.model, parser_args.num, parser_args.counter)
