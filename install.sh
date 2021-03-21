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
sudo apt install -y ros-noetic-desktop-full

if [ "$1" != "build" ]; then
 sudo apt install -y ros-noetic-gazebo-ros-control
fi
