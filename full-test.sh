#!/bin/bash

# 
# this scripts takes qdisc for router as argument
QDISC="$@"
# if qdisc null, set as fq_codel
if [ -z "$QDISC" ]; then
    QDISC="fq_codel"
fi
echo "qdisc: $QDISC"
SND_VM=fyp-1
RCV_VM=fyp-3
ROUT_VM=debian12
TIME=$(date +%Y%m%d-%H%M%S)

# -- helper functions because I'm losing sanity over qemu-agent
# takes two args: vm name and command, then returns pid
vm_exec() {
    # *** DO NOT ADD ANY EXTRA ECHO ***
    local vm=$1
    local cmd=$2
    
    # execute and extract PID
    local result=$(sudo virsh qemu-agent-command "$vm" "{\"execute\":\"guest-exec\", \"arguments\":{\"path\":\"/bin/sh\", \"arg\":[\"-c\", \"$cmd\"], \"capture-output\":true}}")
    local pid=$(echo "$result" | jq -r '.return.pid')
    
    # Return PID
    echo "$pid"
}

# takes vmname and pid, returns human output, does NOT wait until exited = true
vm_exec_output() {
    local vm=$1
    local pid=$2
    
    local status=$(sudo virsh qemu-agent-command "$vm" "{\"execute\":\"guest-exec-status\", \"arguments\":{\"pid\":$pid}}")
    
    local base64_output=$(echo "$status" | jq -r '.return."out-data"')
    
    if [ "$base64_output" != "null" ]; then
        echo "$base64_output" | base64 -d
    else
        # stderr if any
        local error_output=$(echo "$status" | jq -r '.return."err-data"')
        if [ "$error_output" != "null" ]; then
            echo "[err] $(echo "$error_output" | base64 -d)" >&2
            return 1
        fi
        return 0
    fi
}

# execs and gets result, this is a blocking function
vm_exec_get() {
    local vm=$1
    local cmd=$2
    
    # Execute command and get PID
    local pid=$(vm_exec "$vm" "$cmd")
    local status=$(sudo virsh qemu-agent-command "$vm" "{\"execute\":\"guest-exec-status\", \"arguments\":{\"pid\":$pid}}")
    # waiting
    while [ "$(echo "$status" | jq -r '.return.exited')" != "true" ]; do
        sleep 0.2
        status=$(sudo virsh qemu-agent-command "$vm" "{\"execute\":\"guest-exec-status\", \"arguments\":{\"pid\":$pid}}")
    done

    # get base64 output and decode
    local base64_output=$(echo "$status" | jq -r '.return."out-data"')
    if [ "$base64_output" != "null" ]; then
        echo "$base64_output" | base64 -d
    else
        # stderr if any
        local error_output=$(echo "$status" | jq -r '.return."err-data"')
        if [ "$error_output" != "null" ]; then
            echo "[err] $(echo "$error_output" | base64 -d)" >&2
            return 1
        fi
        return 0
    fi
}
## example usage:
#    PID=$(vm_exec $RCV_VM "ip -o addr show to 192.168.11.10 | awk '{print \$2}'")
#    IFNAME=$(vm_exec_output $RCV_VM $PID)
#    echo $IFNAME
#    IFNAME2=$(vm_exec_get $RCV_VM "ip -o addr show to 192.168.11.10 | awk '{print \$2}'")
#    echo $IFNAME2
## end example usage
# -- end helper functions

# setup ifb *inside* VM3, since we want to do traffic shaping at the receiver
get_ifname_rcv() {
    local vm=$1
    local ip=$2
    local ifname=$(vm_exec_get $RCV_VM "ip -o addr show to 192.168.11.10 | awk '{print \$2}'")
    echo $ifname
}
RIFN="$(get_ifname_rcv)"
get_ifname_snd() {
    local vm=$1
    local ip=$2
    local ifname=$(vm_exec_get $SND_VM "ip -o addr show to 192.168.10.10 | awk '{print \$2}'")
    echo $ifname
}
SIFN="$(get_ifname_snd)"

setup_ifb() {
    vm_exec_get $RCV_VM "modprobe ifb numifbs=1"
    vm_exec_get $RCV_VM "ip link set dev ifb0 up"
    vm_exec_get $RCV_VM "tc qdisc del dev ifb0 root"
    vm_exec_get $RCV_VM "tc qdisc del dev $RIFN root"
    vm_exec_get $RCV_VM "tc qdisc replace dev $RIFN handle ffff: ingress"
    vm_exec_get $RCV_VM "tc filter replace dev $RIFN parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0"
}

setup_router() {
    vm_exec_get $ROUT_VM "tc qdisc replace dev veth1 root $QDISC"
    vm_exec_get $ROUT_VM "tc qdisc replace dev vwlan3 root $QDISC"
}

# takes bandwidth and RTT,
# Please supply your units (e.g. mbps, ms) as needed by `tc`.
tune() {
    local bw=$1
    local rtt=$2
    echo "bw=$bw, rtt=$rtt"
    # calculate RTT/2
    local rtt_num=$(echo "$rtt" | grep -o -E '[0-9]+(\.[0-9]+)?')
    local rtt_unit=$(echo "$rtt" | grep -o -E '[a-zA-Z]+')
    local half_rtt=$(echo "scale=2; $rtt_num / 2" | bc)${rtt_unit}
    #echo "$half_rtt"
    # bandwidth parsing, currently unused
    local bw_num=$(echo "$bw" | grep -o -e '[0-9]+(\.[0-9]+)?')
    local bw_unit=$(echo "$bw" | grep -o -e '[a-zA-Z]+')

    # shaping using htb
    #vm_exec_get $RCV_VM "tc qdisc replace dev ifb0 root handle 1: htb default 10"
    #vm_exec_get $RCV_VM "tc qdisc replace dev $RIFN root handle 1: htb default 10"
    #vm_exec_get $RCV_VM "tc class replace dev ifb0 parent 1: classid 1:1 htb rate $bw"
    #vm_exec_get $RCV_VM "tc class replace dev ifb0 parent 1:1 classid 1:10 htb rate $bw"
    #vm_exec_get $RCV_VM "tc qdisc replace dev ifb0 parent 1:10 handle 10: netem delay $half_rtt"
    #vm_exec_get $RCV_VM "tc class replace dev $RIFN parent 1: classid 1:1 htb rate $bw"
    #vm_exec_get $RCV_VM "tc class replace dev $RIFN parent 1:1 classid 1:10 htb rate $bw"
    #vm_exec_get $RCV_VM "tc qdisc replace dev $RIFN parent 1:10 handle 10: netem delay $half_rtt"
    
    # shaping using tbf
    vm_exec_get $RCV_VM "tc qdisc replace dev ifb0 root handle 1: netem delay $half_rtt"
    vm_exec_get $RCV_VM "tc qdisc replace dev $RIFN root handle 1: netem delay $half_rtt"
    vm_exec_get $RCV_VM "tc qdisc replace dev ifb0 parent 1: handle 10: tbf rate $bw burst 32kB latency 50ms"
    vm_exec_get $RCV_VM "tc qdisc replace dev $RIFN parent 1: handle 10: tbf rate $bw burst 32kB latency 50ms"
}


start_capture() {
    # doesnt return pid like iperf cuz tcpdump output not needed
    vm_exec_get $SND_VM "killall tcpdump"
    echo "$SIFN, $TIME"
    local tpid=$(vm_exec $SND_VM "tcpdump -U -i $SIFN -w /tmp/$TIME.pcap")
    vm_exec_output $SND_VM $tpid
    echo $tpid
    # vm_exec $RCV_VM "tcpdump -i $RIFN -w /tmp/$TIME.pcap"
}

stop_capture() {
    vm_exec_get $SND_VM "killall tcpdump"
    # vm_exec_get $RCV_VM "killall tcpdump"
}

# starts iperf3 sending (runs indefinitely), RETURNS PID of send VM's iperf
begin_iperf() {
    vm_exec_get $SND_VM "killall iperf3"
    vm_exec_get $RCV_VM "killall iperf3"
    local ipid=$(vm_exec $RCV_VM "iperf3 -s")
    sleep 0.5
    vm_exec $SND_VM "iperf3 -c 192.168.11.10 -J -t 0 --logfile=/tmp/iperf3_$TIME.json"
    echo $ipid
}

# a bit nuclear, but iperf3 still spits out json on sigkill
finish_iperf() {
    local ipid=$IPFg
    vm_exec_get $SND_VM "killall iperf3"
    vm_exec_get $RCV_VM "killall iperf3"
    sleep 1
    vm_exec_output $SND_VM $ipid
    # todo: will json in json be handled properly
}

####################
#mkdir $TIME
setup_ifb
setup_router
tune 5Mbps 50ms
tune 500Mbps 50ms
TCD=$(start_capture)
IPFg=$(begin_iperf)
echo "tcpdump pid: $TCD"
echo "iperf pid: $IPFg"
# if change interval here, remember to change in analyse.py as well
sleep 5;
tune 2kbps 50ms;
sleep 5;
tune 2Mbps 50ms;
sleep 5;
tune 500kbps 50ms;
sleep 5;
finish_iperf;
sleep 5; # a bit buffer time i guess
stop_capture
scp fyp-vm1:/tmp/$TIME.pcap .
scp fyp-vm1:/tmp/iperf3_$TIME.json .
vm_exec_get $SND_VM "rm -f /tmp/$TIME.pcap /tmp/iperf3_$TIME.json"
# output files should be:
# ./$time.log
# ./$time.pcap

### pre-analyse ###
tshark -r $TIME.pcap -T fields \
  -e frame.time_relative \
  -e tcp.seq \
  -e tcp.analysis.ack_rtt \
  -E header=y \
  -E separator=, \
  -E quote=d \
  -Y "tcp.analysis.ack_rtt" \
  > rtt_$TIME.csv

echo "RTT analysis done, please run python analyse.py rtt_$TIME.csv iperf3_$TIME.json"
echo "rtt_$TIME.csv"