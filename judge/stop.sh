cd ../
./stop.sh

pkill -9 python3
pkill -9 rostopic
pkill -9 -f "/opt/ros/noetic"
pkill -9 -f start.sh
pkill -9 -f "sleep 1d"
