#!/usr/bin/env python

"""
    A pure python multi-ping program, it's simple and light.

    Copyright (c) Dayong Wang, wandering_997@sina.com
    Distributable under the terms of the GNU General Public License
    version 2. Provided with no warranties of any sort.

    Original Pyhton ping code
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    https://github.com/samuel/python-ping/

    Revision history
    ~~~~~~~~~~~~~~~~
    2016/01/23
    Dayong Wang (wandering_997@sina.com)
    Add multiprocessing function which can be enabled by option --process.

    2016/01/18
    Dayong Wang (wandering_997@sina.com)
    Replace getopt with argparse.

    2015/11/06
    Creates by Dayong Wang (wandering_997@sina.com)

    Last commit info:
    ~~~~~~~~~~~~~~~~~
    $LastChangedDate: $
    $Rev: $
    $Author: $
"""

import argparse
import multiprocessing
import re
import subprocess
import threading

import os, sys, socket, struct, select, time


def w_time(time_format = '%Y-%m-%d %H:%M:%S'):

    return time.strftime(time_format, time.localtime(time.time()))


def sys_cmd(str_cmd):

    sp = subprocess.Popen(str_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    str_out = sp.stdout.read()
    str_err = sp.stderr.read()
    sp.wait()
    return [str_out, str_err]


def w_multiprocessing(func_name, func_args, max_process):

    # multi processing
    if func_name == None or func_name == '':
        print('w_multiprocessing() error: func_name is empty.\n')
        return False
    if func_args == None or not isinstance(func_args, list):
        print('w_multiprocessing() error: func_args is wrong.\n')
        return False
    if not isinstance(max_process, int) or max_process == None or max_process == '':
        max_process = 1000

    # create process pool
    process_pool = list()
    for i in range(0, len(func_args)):
        p = multiprocessing.Process(target=func_name, args=func_args[i])
        process_pool.append(p)

    # execute processs for max_process number of processs each time
    process_count = len(process_pool)
    if process_count > max_process:
        i_begin = 0
        i_end = 0
        round_num = process_count / max_process
        if process_count % max_process > 0:
            round_num += 1
        # max_process: How many processs (test) could be executed at one time
        for j in range(0, round_num):
            i_begin = j * max_process
            if j == round_num - 1:                 # the last round
                i_end = process_count
            else:
                i_end = i_begin + max_process
            # start processs
            for i in range(i_begin, i_end):
                process_pool[i].start()
            # terminate processs
            for i in range(i_begin, i_end):
                process_pool[i].join()
    # === process_count <= max_process ===
    else:
        # start processs
        for i in range(0, process_count):
            process_pool[i].start()
        # terminate processs
        for i in range(0, process_count):
            process_pool[i].join()
    # ========== Run processs - End ==========

#___ End of w_multiprocessing() ____


def w_threading(func_name, func_args, max_thread):

    # multi threading
    if func_name == None or func_name == '':
        print('w_threading() error: func_name is empty.\n')
        return False
    if func_args == None or not isinstance(func_args, list):
        print('w_threading() error: func_args is wrong.\n')
        return False
    if not isinstance(max_thread, int) or max_thread == None or max_thread == '':
        max_thread = 1000

    # create thread pool
    thread_pool = list()
    for i in range(0, len(func_args)):
        th = threading.Thread(target=func_name, args=func_args[i])
        thread_pool.append(th)

    # execute threads for max_thread number of threads each time
    thread_count = len(thread_pool)
    if thread_count > max_thread:
        i_begin = 0
        i_end = 0
        round_num = thread_count / max_thread
        if thread_count % max_thread > 0:
            round_num += 1
        # max_thread: How many threads (test) could be executed at one time
        for j in range(0, round_num):
            i_begin = j * max_thread
            if j == round_num - 1:                 # the last round
                i_end = thread_count
            else:
                i_end = i_begin + max_thread
            # start threads
            for i in range(i_begin, i_end):
                thread_pool[i].start()
            # terminate threads
            for i in range(i_begin, i_end):
                thread_pool[i].join()
    # === thread_count <= max_thread ===
    else:
        # start threads
        for i in range(0, thread_count):
            thread_pool[i].start()
        # terminate threads
        for i in range(0, thread_count):
            thread_pool[i].join()
    # ========== Run threads - End ==========

#___ End of w_threading() ____


#/////////////////////// python ping - start ///////////////////////


# From /usr/include/linux/icmp.h; your milage may vary.
ICMP_ECHO_REQUEST = 8 # Seems to be the same on Solaris.

def checksum(source_string):
    """
    I'm not too confident that this is right but testing seems
    to suggest that it gives the same answers as in_cksum in ping.c
    """
    sum = 0
    countTo = (len(source_string)/2)*2
    count = 0
    while count<countTo:
        thisVal = ord(source_string[count + 1])*256 + ord(source_string[count])
        sum = sum + thisVal
        sum = sum & 0xffffffff # Necessary?
        count = count + 2

    if countTo<len(source_string):
        sum = sum + ord(source_string[len(source_string) - 1])
        sum = sum & 0xffffffff # Necessary?

    sum = (sum >> 16)  +  (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff

    # Swap bytes. Bugger me if I know why.
    answer = answer >> 8 | (answer << 8 & 0xff00)

    return answer


def receive_one_ping(my_socket, ID, timeout):
    """
    receive the ping from the socket.
    """
    timeLeft = timeout
    while True:
        startedSelect = time.time()
        whatReady = select.select([my_socket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []: # Timeout
            return

        timeReceived = time.time()
        recPacket, addr = my_socket.recvfrom(1024)
        icmpHeader = recPacket[20:28]
        type, code, checksum, packetID, sequence = struct.unpack(
            "bbHHh", icmpHeader
        )
        # Filters out the echo request itself. 
        # This can be tested by pinging 127.0.0.1 
        # You'll see your own request
        if type != 8 and packetID == ID:
            bytesInDouble = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
            return timeReceived - timeSent

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return


def send_one_ping(my_socket, dest_addr, ID):
    """
    Send one ping to the given >dest_addr<.
    """
    dest_addr  =  socket.gethostbyname(dest_addr)

    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    my_checksum = 0

    # Make a dummy heder with a 0 checksum.
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
    bytesInDouble = struct.calcsize("d")
    data = (192 - bytesInDouble) * "Q"
    data = struct.pack("d", time.time()) + data

    # Calculate the checksum on the data and the dummy header.
    my_checksum = checksum(header + data)

    # Now that we have the right checksum, we put that in. It's just easier
    # to make up a new header than to stuff it into the dummy.
    header = struct.pack(
        "bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1
    )
    packet = header + data
    my_socket.sendto(packet, (dest_addr, 1)) # Don't know about the 1


#
# 2015/11/07  Dayong Wang
#
# Remark below line because it raises "[Errno 93] Protocol not supported"
# sometimes. And this is maybe a performance problem of getprotobyname().
# And add icmp as the 3rd option to do_one().

#def do_one(dest_addr, timeout):
#    """
#    Returns either the delay (in seconds) or none on timeout.
#    """
#    icmp = socket.getprotobyname("icmp")       


# 2015/11/07  Dayong Wang added one line below
icmp = socket.getprotobyname("icmp")

def do_one(dest_addr, timeout, icmp = 1):
    """
    Returns either the delay (in seconds) or none on timeout.
    """
    try:
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    except socket.error, (errno, msg):
        if errno == 1:
            # Operation not permitted
            msg = msg + (
                " - Note that ICMP messages can only be sent from processes"
                " running as root."
            )
            raise socket.error(msg)
        raise # raise the original error

    my_ID = os.getpid() & 0xFFFF

    send_one_ping(my_socket, dest_addr, my_ID)
    delay = receive_one_ping(my_socket, my_ID, timeout)

    my_socket.close()
    return delay


def verbose_ping(dest_addr, timeout = 2, count = 4):
    """
    Send >count< ping to >dest_addr< with the given >timeout< and display
    the result.
    """
    for i in xrange(count):
        print "ping %s..." % dest_addr,
        try:
            delay  =  do_one(dest_addr, timeout)
        except socket.gaierror, e:
            print "failed. (socket error: '%s')" % e[1]
            break

        if delay  ==  None:
            print "failed. (timeout within %ssec.)" % timeout
        else:
            delay  =  delay * 1000
            print "get ping in %0.4fms" % delay
    print


def w_verbose_ping(dest_addr, count = 1, interval = 0.01, timeout = 1, shell_ping = False, silence = False):

    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    cmd_out  = ''
    pkt_loss = 0
    pkt_recv = 0
    rtt_min  = 0.0
    rtt_avg  = 0.0
    rtt_max  = 0.0
    rtt_sum  = 0.0
    msg_header = "ping %s:" % (dest_addr)
    for pkt_sent in xrange(count):
        try:
            delay = do_one(dest_addr, timeout, icmp)
        except socket.gaierror, e:
            print("%s failed (socket error: '%s')" % (msg_header, e[1]))
            return ''
        if delay  ==  None:
            pkt_loss = pkt_loss + 1
            if not silence:
                cmd_out = "%s%s failed (timeout within %s sec)\n" % (cmd_out, msg_header, timeout)
        else:
            pkt_recv = pkt_recv + 1
            delay = delay * 1000
            rtt_sum = rtt_sum + delay
            if rtt_max < delay:
                rtt_max = delay
            if rtt_min > delay or rtt_min == 0:
                rtt_min = delay
            if not silence:
                cmd_out = "%s%s icmp_seq=%d time=%0.4f ms\n" % (cmd_out, msg_header, pkt_sent, delay)
        time.sleep(interval)
    if pkt_recv > 0:
        pkt_sent = pkt_sent + 1
        loss = pkt_loss / pkt_sent
        rtt_avg = rtt_sum / pkt_recv
        cmd_out = """
%s
--- [%s] %s ping statistics ---
%d packets transmitted, %d received, %0.2f%% packet loss, time %0.3fms
rtt min/avg/max/mdev = %0.3f/%0.3f/%0.3f/0.000 ms
""" % ( cmd_out,
        now, dest_addr, 
        pkt_sent, pkt_recv, loss, rtt_sum,
        rtt_min, rtt_avg, rtt_max)
        if shell_ping:
            return cmd_out
        else:
            return "%s, %s, %s, %s, %0.2f%%, %0.3f, %0.3f, %0.3f" % \
                   (now, dest_addr, pkt_sent, pkt_recv, loss, rtt_min, rtt_avg, rtt_max)
    else:
        return ''


#/////////////////////// python ping - end ///////////////////////


def w_ping(dst_ip, ping_count=1, ping_interval=0.01, ping_timeout=1, datadir=".", silent=False, shell_ping=False, ping_src="n/a"):

    # dst_ip
    if re.search("^([0-9]{1,3}\.){3}[0-9]{1,3}$", dst_ip) == None:
        return False

    # ping_count
    if ping_count < 0 or ping_count > 1000:
        ping_count = 1

    # do ping
    cmd_out = w_verbose_ping(dst_ip, ping_count, ping_interval, ping_timeout, shell_ping)
    if cmd_out == '':
        return False
    if not shell_ping:
        #timestamp, dst_ip, sent, recieved, loss, min, avg, max, src_ip
        cmd_out = "%s, %s" % (cmd_out, ping_src)

    if not silent:
        print(cmd_out)

    # write to file
    output_file  = "%s/%s" % (datadir, dst_ip)
    output_path = os.path.dirname(output_file)
    if not os.path.exists(output_path):
        try:
            cmd_mkdir = 'mkdir -p %s' % (output_path)
            sys_cmd(cmd_mkdir)
        except:
            print('[%s] Error: mkdir %s failed!' % (w_time(), output_path))
            return False
 
    try:
        f_out = open(output_file, 'a')
        f_out.write("%s\n" % (cmd_out))
        f_out.close()
    except:
        print('[%s] Error: file %s is failed to write.' % (w_time(), output_file))
        return False

    return True



if __name__ == '__main__':

    p = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description="  This is a pure python ping, it was designed for pinging a lot of IP addresses.",
            epilog='''

Log format:

    yyyy-mm-dd HH:MM:SS, ip, pkt_sent, pkt_recv, loss, rtt_min, rtt_avg, rtt_max, src


Example:

    %s --ip 192.168.0.1
    %s --ipfile ./ip.test --datadir /tmp/test --interval 0 --timeout 0.1

                   ''' % (sys.argv[0], sys.argv[0])
        )

    p.add_argument("--src",       type=str,   default="n/a", help="Source name of ping, is hostname mostly, default is n/a.")
    p.add_argument("--ip",        type=str,   help="Destination IP list to ping.")
    p.add_argument("--ipfile",    type=str,   help="Destination IP list file to ping.")
    p.add_argument("--datadir",   type=str,   default=".",   help='''Where the ping result to be stored, default is current directory. 
Example:
/var/log/w-ping/$(date "+%%Y")/$(date "+%%Y%%m%%d")/
''')

    p.add_argument("--count",     type=int,   default=1,     help="Same to -c of ping, accepts 0 to 1000, default is 1.")
    p.add_argument("--interval",  type=float, default=0.01,  help="Same to -i of ping, accepts 0 to 60, default is 0.01.")
    p.add_argument("--timeout",   type=int,   default=1,     help="Time to wait for ping executing, default is 1 seconds.")
    p.add_argument("--max",       type=int,   default=1000,  help="The maximum threads/processes could be spread each time, default is 1000.")
    p.add_argument("--shellping", action="store_true", help="Use traditional shell ping output instead of csv output.")
    p.add_argument("--silent",    action="store_true", help="Silence mode.")
    p.add_argument("--process",   action="store_true", help="Use multi-process instead of multi-thread.")

    args = p.parse_args()

    # func_name
    func_name = w_ping

    # func_args
    func_args = list()

    # ip
    list_ip = list()
    if args.ip:
        list_ip = args.ip.split(',')
    elif args.ipfile:
        if not os.path.exists(args.ipfile):
            print('%s does not exist, use -h to get more help.\n' % (args.ipfile))
            sys.exit()
        f_ip = open(args.ipfile)
        list_ip = f_ip.readlines()
        f_ip.close()
    else:
        p.print_help()
        sys.exit()

    # Prepare threading
    for dst_ip in list_ip:
        func_args.append([dst_ip.strip(), args.count, args.interval, args.timeout, args.datadir, args.silent, args.shellping, args.src])
  
    if args.process:
        # Start multi-processing
        try:
            w_multiprocessing(func_name, func_args, args.max)
        except:
            print("Fail to run w_multiprocessing().")
            pass
    else:
        # Start multi-threading
        try:
            w_threading(func_name, func_args, args.max)
        except:
            print("Fail to run w_threading().")
            pass

    # End
    sys.exit()


