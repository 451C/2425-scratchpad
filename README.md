## -1. Setup
### VM Setup
TODO: VM1 - VM2 - VM3 diagram

Notation:
| VM1  | content server  |
| VM2  | router          |
| VM3  | wireless client |
| net1 | "the internet"  |
| net2 | behind NAT      |

### Baselines
We don't have TCP ABC and Copa in kernel :/
Cubic + (pfifo|CoDel|cake)
~~or if you wanna bother with BBRv3 https://github.com/CachyOS/kernel-patches/blob/master/6.13/0003-bbr3.patch~~

## 0. Capture
1. Config VMs
    - VM3 - Congestion: `tc qdisc add dev enp7s0 root netem delay 20ms 10ms distribution normal loss 1.5% 25% rate 2Mbit`
    - VM2 - Change qdisc: `tc qdisc replace dev vwlan3 root fq_codel && tc qdisc replace dev veth1 root codel`
    
2. Generate traffic
    - 3 minutes of TCP packets :P
    - VM3: `iperf3 -s`
    - VM1: `iperf3 -c [VM3 IP] -t 180`

3. Capture frfr
    - VM1: `tcpdump -i [net1 interface] -w capture_{NAME}.pcap host [VM3 IP]`
    - stop after iperf finish

probably write a script to automate this

## 1. RTT distribution


