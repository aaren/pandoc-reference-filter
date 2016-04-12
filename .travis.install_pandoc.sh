#!/usr/bin/env bash

mkdir ~/pandoc
wget https://github.com/jgm/pandoc/releases/download/1.17.0.2/pandoc-1.17.0.2-1-amd64.deb
dpkg --extract pandoc-1.17.0.2-1-amd64.deb ~/pandoc/1.17
export PATH=~/pandoc/$PANDOC/usr/bin/:$PATH

echo $PANDOC
type -p pandoc
pandoc --version
