#!/bin/bash

# options: -bw [bandwidth]
#          -rtt [RTT]
#          [-reset]
# Please supply your units (e.g. mbps, ms) as required by `tc`.
# IMPORTANT: run setup.sh before this!!!

VMNAME=fyp-3
VIF=$(sudo virsh domiflist $VMNAME | awk '$3 == "net2" {print $1}')

# very basic sanity check: does ifb exist
ip link | grep -q "ifb0" || { echo "no ifb device found!"; exit 1; }

BW=5Mbps
RTT=50ms
# parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -bw)
            BW="$2"
            shift 2
            ;;
        -rtt)
            RTT="$2"
            shift 2
            ;;
        -reset)
            ./setup.sh
            echo "--reset done--"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo "if: $VIF, bandwidth: $BW, rtt: $RTT"

# calculate RTT/2
if [[ -n "$RTT" ]]; then
    RTT_NUM=$(echo "$RTT" | grep -o -E '[0-9]+(\.[0-9]+)?')
    RTT_UNIT=$(echo "$RTT" | grep -o -E '[a-zA-Z]+')
    HALF_RTT=$(echo "scale=2; $RTT_NUM / 2" | bc)${RTT_UNIT}
fi
echo "[debug]half RTT: $HALF_RTT"

if [[ -n "$BW" ]]; then
    BW_NUM=$(echo "$BW" | grep -o -E '[0-9]+(\.[0-9]+)?')
    BW_UNIT=$(echo "$BW" | grep -o -E '[a-zA-Z]+')
fi

#sudo tc qdisc replace dev ifb0 root handle 1: netem delay $HALF_RTT
#sudo tc qdisc replace dev $VIF root handle 1: netem delay $HALF_RTT
#sudo tc qdisc replace dev ifb0 parent 1: handle 10: tbf rate $BW burst 32kB latency 50ms
#sudo tc qdisc replace dev vnet18 parent 1: handle 10: tbf rate $BW burst 32kB latency 50ms

# [HTB]
# htb bandwidth limiting instead of tbf https://serverfault.com/a/386791
# NOTE: sending rate fluctuates like crazy
sudo tc qdisc replace dev ifb0 root handle 1: htb default 10
sudo tc qdisc replace dev $VIF root handle 1: htb default 10
sudo tc class replace dev ifb0 parent 1: classid 1:1 htb rate $BW
sudo tc class replace dev ifb0 parent 1:1 classid 1:10 htb rate $BW
sudo tc qdisc replace dev ifb0 parent 1:10 handle 10: netem delay $HALF_RTT
sudo tc class replace dev $VIF parent 1: classid 1:1 htb rate $BW
sudo tc class replace dev $VIF parent 1:1 classid 1:10 htb rate $BW
sudo tc qdisc replace dev $VIF parent 1:10 handle 10: netem delay $HALF_RTT

