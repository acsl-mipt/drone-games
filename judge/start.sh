#!/bin/bash

s_dir=../

if [[ -z "$1" ]]; then
  echo "$0 rc_file"
  exit
fi

. $1

if [[ -z "$sim" || -z "$type" || -z "$num" || -z "$world" || -z "$u_cmd" ]]; then
  echo "invalid vars in $1"
  exit
fi

if [[ -z "$team" ]]; then
  team="Неизвестная_команда"
fi


model="iris"
if [ "$type" == "vtol" ]; then
  model="standard_vtol"
fi

j_params=""
if [ "$sim" == "formation" ]; then
 j_params="$model $num $sim $team"
fi
if [ "$sim" == "race" ]; then
 j_params="$model $num $sim $team"
fi
if [[ -z "$j_params" ]]; then
  echo "invalid sim in $1"
  exit
fi

s_cmd="./${sim}.sh prof ${type} ${num} ${world}"
j_cmd="./ui.py ${j_params}"

out_d="out_${sim}_${type}_${world}_${num}"
mkdir -p $out_d

pushd $s_dir >/dev/null
  echo "starting $s_cmd"
  $s_cmd
popd >/dev/null

echo "waiting topics ..."
./echo_pos.sh $num 1 >/dev/null 2>/dev/null

j_log=judge.log
pushd $out_d >/dev/null
  echo "`date` starting $j_cmd" | tee -a $j_log
  ../$j_cmd | tee -a $j_log &
popd >/dev/null

u_log=$out_d/user.log
echo "`date` starting $u_cmd" | tee -a $u_log
$u_cmd >> $u_log &

echo "Press CTRL+C to stop all"
sleep 1d
