#!/bin/bash

gm="iris"
n=1

if [ "$1" ]; then
 gm=$1
 shift
fi

if [ "$1" ]; then
 n=$1
 shift
fi

cws="$HOME/catkin_ws"

./stop.sh
./multiple-sitl/start.rb --gazebo_model $gm -n $n --firmware ./Firmware --firmware_initd ./multiple-sitl/px4 --catkin_ws $cws --nospawn $@
