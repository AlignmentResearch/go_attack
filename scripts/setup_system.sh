#!/bin/bash

# Set up a system we have root access on (e.g. cloud VM) with appropriate tools
# needed to run Docker compose and auxiliary utilities.

sudo apt-get install -y python3-pip python3-virtualenv gpustat
sudo pip install docker-compose
sudo pip install tensorboard
