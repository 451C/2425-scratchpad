#!/bin/bash

# ###################################################
# #  This script is for inital setup of IFB device  #
# #  for bandwidth & RTT change please use tune.sh  #
# ###################################################
# also called by tune.sh when neccessary
# ref: https://serverfault.com/questions/350023/tc-ingress-policing-and-ifb-mirroring

# get VM3 / net2 tap interface name
VMNAME=fyp-3
VIF=$(sudo virsh domiflist $VMNAME | awk '$3 == "net2" {print $1}')
echo 'setup ifb on interface: $VIF'

# setup ifb
sudo modprobe ifb numifbs=1
sudo ip link set dev ifb0 up

# redirect ingress traffic 
# mindlessly resetting things here, should be safe to ignore "Cannot delete qdisc with handle of zero"
sudo tc qdisc del dev ifb0 root
sudo tc qdisc del dev $VIF root
sudo tc qdisc replace dev $VIF handle ffff: ingress
sudo tc filter replace dev $VIF parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0

