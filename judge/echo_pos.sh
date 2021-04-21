num=$1
c=$2

for (( n=1 ; n<=$num; n++ ))
do
  rostopic echo -n $c /mavros$n/local_position/pose &
done

wait
