#!/bin/bash

num=6
model="iris"
world="formation.world"

if [ "$1" == "prof" ]; then
  arg="--gazebo_ros"
elif [ "$1" == "nonprof" ]; then
  arg=""
else
  echo "$0 (prof | nonprof) [mc | vtol] [num] [world]"
  exit
fi

if [ "$2" == "vtol" ]; then
  model="standard_vtol"
fi

if [ "$3" != "" ]; then
  num=$3
fi

if [ "$4" != "" ]; then
  world=$4
fi

./start.sh $model $num gazebo/worlds/$world --pose_list places.txt --ref_point 0,-72,0.1 $arg $@

if [ "$1" == "prof" ]; then
  suf=""
  args="--names T E C T"

  if [ "$world" == "formation_2.world" ]; then
    suf="_2/$num"
    args="--names C S P A"
  fi

  ./bin/formations_gen.py $model $num formation/borders.txt formation/test_fs${suf}/ $args &
fi
