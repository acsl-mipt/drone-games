#!/bin/bash

num=1
pkg="cargo"

source params1.sh

AIRSIM_PKG=$pkg ./start.sh -n $num --ref_point 110,520,-100 --home-gps 1,1,220 $@

sleep 3

if [ $mode == "exp" ]; then
  ./bin/cargo_drop.py --gps_ref 1 1 220 iris 1 tasks/cargo/1/gps_droppoint.pts tasks/cargo/1/range.txt &
fi

read -p "Press enter to stop ..."
./stop.sh



