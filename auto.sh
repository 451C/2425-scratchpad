#!/bin/bash

# the "full-auto" experimental setup

# timestamp
TIME=$(date +%Y%m%d-%H%M%S)

# (1) setup interfaces
./tune.sh -reset -bw 15Mbit -rtt 50ms

# (2) tcpdump start capture
./capture.sh $TIME &

# (3) iperf3 (run with virsh qemu-agent)
sudo virsh qemu-agent-command fyp-1 '{"execute":"guest-exec", "arguments":{"path":"bash", "arg":["-c", "killall iperf3"], "capture-output":false}}'
sudo virsh qemu-agent-command fyp-3 '{"execute":"guest-exec", "arguments":{"path":"bash", "arg":["-c", "killall iperf3"], "capture-output":false}}'
sudo virsh qemu-agent-command fyp-3 '{"execute":"guest-exec", "arguments":{"path":"iperf3", "arg":["-s", "-p", "5123"], "capture-output":false}}'
sudo virsh qemu-agent-command fyp-1 '{"execute":"guest-exec", "arguments":{"path":"bash", "arg":["-c", "iperf3 -c 192.168.11.10 -p 5123 -t 60 --json-stream > /tmp/$TIME.json"], "capture-output":false}}'
# FIX: json not working

# (4) in this 60 secs, change ABW in host
sleep 10
./tune.sh -bw 7Mbit -rtt 50ms
sleep 15
./tune.sh -bw 2Mbit -rtt 50ms
sleep 15
./tune.sh -bw 600kbit -rtt 50ms
sleep 20
echo "iperf3 sending finished" # bruh

sleep 5 # buffer time
sudo virsh qemu-agent-command fyp-1 '{"execute":"guest-exec", "arguments":{"path":"bash", "arg":["-c", "killall iperf3"], "capture-output":false}}'
sudo virsh qemu-agent-command fyp-3 '{"execute":"guest-exec", "arguments":{"path":"bash", "arg":["-c", "killall iperf3"], "capture-output":false}}'
# (5) tshark stop capture (a bit nuclear)
sudo killall tcpdump
echo "tcpdump killed"

# note: tcpdump output saved in current dir
# get iperf logs back
#scp fyp-vm1:/tmp/$TIME.json .

## (6) analyse!!
# - convert rtt pcap to csv
# - plot with iperf logs
#tshark -r capture/$TIME.pcap -T fields -e frame.time_relative -e tcp.analysis.ack_rtt -Y "tcp.analysis.ack_rtt" -E header=y -E separator=, -E quote=d -E occurrence=f > rtt_$TIME.csv

