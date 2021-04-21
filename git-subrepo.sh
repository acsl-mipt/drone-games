#!/bin/sh

url="https://github.com/acsl-mipt/git-commands.git"
f="./git-commands/git-subrepo"

#init git-subrepo
if [ ! -x $f ];then
  git clone $url
  if [ ! -x $f ];then
    exit
  fi
fi

$f $@
