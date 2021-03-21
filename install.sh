#!/bin/bash

dir=`pwd`/`dirname $0`/

cd $dir
./git-subrepo.sh

f="all"

if [ "$1" == "build" ]; then
 f="prepare"
fi

./multiple-sitl/install/$f.sh default $dir/Firmware

# Install full version of ROS Noetic. It could help in development process
source /opt/ros/noetic/setup.bash
sudo apt install -y ros-noetic-desktop-full

source /opt/ros/noetic/setup.bash
sudo apt install -y python3-rosdep python3-rosinstall python3-rosinstall-generator python3-wstool build-essential

sudo rosdep init
rosdep update

cd ~/catkin_ws/src; catkin_init_workspace; cd -; cd ~/catkin_ws; catkin_make; cd -;

echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
source ~/.bashrc

if [ "$1" != "build" ]; then
 sudo apt install -y ros-noetic-gazebo-ros-control
fi
