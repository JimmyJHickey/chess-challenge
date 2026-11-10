#!/bin/bash

/home/pi/.pyenv/shims/python3 /home/pi/git/chess-challenge/run.py
cd /home/pi/git/jimmyjhickey.com

git add chess.md img/chess/
git commit -m "chess stats updates $(date '+%Y-%m-%d %H:%M:%S')"
git push
