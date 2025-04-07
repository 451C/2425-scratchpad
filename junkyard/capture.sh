#!/bin/bash

# optionally specify filename (useful for automation)
if [ -z "$1" ]; then
    NAME=$(date +"%Y%m%d_%H%M%S")
else
    NAME="$1"
fi

# S prefix means "sender", R means receiver
SVMNAME=fyp-1
RVMNAME=fyp-3

SVIF=$(sudo virsh domiflist $SVMNAME | awk '$3 == "net1" {print $1}')
RVIF=$(sudo virsh domiflist $RVMNAME | awk '$3 == "net2" {print $1}')

# Sender & Receiver IP
SIP="192.168.10.10"
RIP="192.168.11.10"

#echo "TCP packets between $SIP and $RIP on $SVIF, Ctrl-C to stop"
sudo tcpdump -i $SVIF -w "capture/s_$NAME.pcap" host $RIP or $SIP &
sudo tcpdump -i $RVIF -w "capture/r_$NAME.pcap" host $RIP or $SIP &

