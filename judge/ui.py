#!/usr/bin/env python3
# coding=utf8

import argparse
import os
import pickle
import signal
import sys
from pathlib import Path
from threading import Thread

import rospy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QWidget, QGridLayout
from std_msgs.msg import String

from main_widget import MainWidget

LABEL_HEIGHT = 70
FILENAME = 'counter'
parser_args = None


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        central_widget = QWidget()
        main_layout = QGridLayout()

        # noinspection PyUnresolvedReferences
        if parser_args.type == 'formation':
            dis_label = QLabel("Дисциплина\nСинхронный полет")
            num_label = QLabel("Formation_2 ({})".format(counter))
        else:
            dis_label = QLabel("Дисциплина\nКомандная гонка")
            num_label = QLabel("Race_2 ({})".format(counter))

        # noinspection PyUnresolvedReferences
        name_label = QLabel("Команда\n{}".format(str(parser_args.team)))

        dis_label.setStyleSheet("QLabel { background-color: #808080; color: white; font-size: 24px; }")
        name_label.setStyleSheet("QLabel { background-color: #808080; color: white; font-size: 24px; }")
        num_label.setStyleSheet("QLabel { background-color: #808080; color: white; font-size: 24px; }")

        dis_label.setFixedHeight(LABEL_HEIGHT)
        name_label.setFixedHeight(LABEL_HEIGHT)
        num_label.setFixedHeight(LABEL_HEIGHT)

        dis_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        name_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        num_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        main_layout.addWidget(dis_label, 0, 0)
        main_layout.addWidget(name_label, 0, 1)
        main_layout.addWidget(num_label, 0, 2)

        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 3)
        main_layout.setColumnStretch(2, 3)

        self.img_label = QLabel("")
        self.img_label.setStyleSheet("QLabel { margin: 0px 0px 0px 20px; }")
        # noinspection PyUnresolvedReferences
        if parser_args.type == 'formation':
            self.img_label.setFixedHeight(482)
            self.img_label.setFixedWidth(482)
        else:
            self.img_label.setFixedHeight(362)
            self.img_label.setFixedWidth(362)

        # noinspection PyUnresolvedReferences
        if parser_args.type == 'formation':
            self.main_widget = MainWidget(formation=True, prnt=self)
        else:
            self.main_widget = MainWidget(formation=False, prnt=self)
        main_layout.addWidget(self.main_widget, 1, 0)

        main_layout.addWidget(self.img_label, 2, 0)

        main_layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        rospy.init_node('ui', anonymous=True)
        rospy.Subscriber('/collisions', String, self.main_widget.collisions_cb)
        rospy.Subscriber('/final', String, self.main_widget.final_cb)

        # noinspection PyUnresolvedReferences
        if parser_args.type == 'formation':
            rospy.Subscriber('/side_time', String, self.main_widget.side_time_cb)
            rospy.Subscriber('/msd_current', String, self.main_widget.msd_current_cb)
            rospy.Subscriber('/msd_overall', String, self.main_widget.msd_overall_cb)
            rospy.Subscriber('/reformation', String, self.main_widget.reformation_cb)
        else:
            rospy.Subscriber('/passes', String, self.main_widget.passes_cb)
            rospy.Subscriber('/times', String, self.main_widget.times_cb)


def arguments():
    global parser_args

    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="model name")
    parser.add_argument("num", type=int, help="models number")
    parser.add_argument("type", help="formation or race")
    parser.add_argument("team", help="team name")

    parser_args = parser.parse_args()


# noinspection PyUnusedLocal
def sigint_handler(*args):
    QApplication.quit()


if __name__ == '__main__':
    # signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGINT, sigint_handler)

    app = QApplication(sys.argv)

    arguments()

    if Path(FILENAME).is_file():
        with open(FILENAME, 'rb') as file:
            counter = pickle.load(file) + 1
    else:
        counter = 1
    with open(FILENAME, 'wb') as file:
        pickle.dump(counter, file)

    # noinspection PyUnresolvedReferences
    if parser_args.type == 'formation':
        # noinspection PyUnresolvedReferences
        Thread(target=os.system,
               args=(
                   "python3 {}/formation_judge.py {} {} {}".format(os.path.dirname(__file__),
                                                                   parser_args.model,
                                                                   parser_args.num,
                                                                   counter,
                                                                   parser_args.team),)
               ).start()
    else:
        # noinspection PyUnresolvedReferences
        Thread(target=os.system,
               args=(
                   "python3 {}/race_judge.py {} {} {}".format(os.path.dirname(__file__),
                                                              parser_args.model,
                                                              parser_args.num,
                                                              counter,
                                                              parser_args.team),)).start()

    window = MainWindow()

    window.showMaximized()

    app.exec_()
