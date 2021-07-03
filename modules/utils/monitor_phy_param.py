import argparse
import getopt
import sys
import datetime
import time
import subprocess
from time import sleep
from threading import Thread
from getmac import get_mac_address
from netaddr import *

#default rssi monitoring interval: 5sec
rssi_mon_interval = 5
#default interface
interface = "wlan0"
mac_addr_filter = "FF:FF:FF:FF:FF:FF"

def is_csi_supported():
    soc_version_cmd = "cat /proc/cpuinfo | grep 'Revision' | awk '{print $3}'"
    proc = subprocess.Popen(soc_version_cmd, stdout=subprocess.PIPE, shell=True)
    soc_version = proc.communicate()[0].decode('utf-8').strip()
    print("SOC VERSION:"+soc_version)
    if ((soc_version == 'a020d3') or (soc_version == 'b03114')):
        print("RPI nexmon CSI is supported, SOC VERSION:"+soc_version)
        return  1
    else:
       return 0

def capture_csi():
    global interface
    global mac_addr_filter
    #Get CSI extractor filter
    csi_filter_cmd = "makecsiparams -c 157/80 -C 1 -N 1 -m " + mac_addr_filter + " -b 0x88"
    proc = subprocess.Popen(csi_filter_cmd, stdout=subprocess.PIPE, shell=True)
    filter_conf = proc.communicate()[0].decode('utf-8').strip()
    print(filter_conf)

   #Configure CSI extractor
    csi_ext_cmd = "nexutil -I" + interface + " -s500 -b -l34 -v"+filter_conf
    proc = subprocess.Popen(csi_ext_cmd, stdout=subprocess.PIPE, shell=True)
    print(csi_ext_cmd)

    en_monitor_mode_cmd = "iw phy `iw dev " + interface + " info | gawk '/wiphy/ {printf \"phy\" $2}'` interface add mon0 type monitor && ifconfig mon0 up"
    proc = subprocess.Popen(en_monitor_mode_cmd, stdout=subprocess.PIPE, shell=True)
    print(en_monitor_mode_cmd)

    #Make sure injector is generating unicast traffic to mac_addr_filter
    #destination, Start tcpdump to capture  the CSI
    dump_cmd = "tcpdump -G 60 -i " + interface + " dst port 5500 -w csi-%m_%d_%Y_%H_%M_%S.pcap"
    proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, shell=True)

def get_mac_oui():
    mac = EUI(get_mac_address(interface))
    oui = mac.oui
    print(oui.registration().address)
    return oui

def get_rssi():
    global interface
    cmd = "iw dev " + interface + " station dump | grep 'signal:' | awk '{print $2}'"
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    rssi = proc.communicate()[0].decode('utf-8')
    return rssi

def log_rssi():
    global rssi_mon_interval
    fn_suffix=str(datetime.datetime.now().strftime('%m_%d_%Y_%H_%M_%S'))
    log_file_path = '/var/log/'
    log_file_name =  'rssi'+fn_suffix+'.txt'
    while True:
        f = open(log_file_path+log_file_name, 'a')
        rssi_sta = get_rssi()
        print(rssi_sta)
        f.write(str(time.time())+' '+rssi_sta)
        f.close()
        sleep(rssi_mon_interval)

if __name__=='__main__':

    # Construct the argument parser
    phy_cfg = argparse.ArgumentParser()

    # Add the arguments to the parser
    phy_cfg.add_argument("-r", "--rssi_period", required=True, help="RSSI monitoring period Ex: 5 (equals to 5 sec)")
    phy_cfg.add_argument("-i", "--interface", required=True)
    args = phy_cfg.parse_args()

    #populate args
    rssi_mon_interval = int(args.rssi_period)
    interface = args.interface

    val = is_csi_supported()
    if (val == 1):
        Thread(target=capture_csi).start()

    Thread(target=log_rssi).start()

