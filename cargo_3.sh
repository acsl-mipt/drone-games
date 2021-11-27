#!/bin/bash

num=3
pkg="cargo_3"

source params1.sh

AIRSIM_PKG=$pkg ./start.sh -n $num --ref_point 106,505,-115 --home-gps 1,1,220 $@

sleep 3

if [ $mode == "exp" ]; then
  ./bin/cargo_drop.py --gps_ref 1 1 220 iris $num tasks/cargo/3/gps_droppoint.pts tasks/cargo/3/range.txt &
fi

read -p "Press enter to stop ..."
./stop.sh
