"""
Get a server's system information and save to JSON. 
This will be deployed to epiphyte, enterprise, 
serenity, and blacksun. The following list shows 
what's included in the JSON file, but it isn't 
comprehensive. 

Would be nice to convert to Fabric, which would 
enable us to get all of the servers' information
from a centralized location. (Can also do this via
ssh but just reading one file per server by ssh is 
probably faster.)

===================JSON INCLUDES===================
System Information: 
	- System distribution information (name, release, version, etc)
	- Processor information 
	- RAM Usage (Used, Free in MB and %)
		- Total (MB)
		- Free (MB, %)
		- Available (MB, %)
		- Used (MB, %)
	- CPU
		- Load avg. (1, 5, 15 min avg)
		- User 
		- System 
		- Idle 
		- I/O Wait 
		- #Cores 
	- Network: list all:
		- interfaces
		- ips 
		- RX/s 
		- TX/s 
		- **TODO: additional:
			- bytes sent/received 
			- packets sent/received 
			- errors in/out
			- dropped in/out
			- connections (FD/PID, family, type, local address, remote address, state)
	- Disks: list all:
		- devices
		- mounted
		- total GB, %
		- used GB, %
		- free GB, %
		- options 
		- type 
		- disk IO 
			- read count/bytes
			- write count/bytes 
			- read time (ms) 
	- Swap
		- Total (bytes)
		- Used (bytes, %)
		- free (bytes, %)
		- swapped in (bytes)
		-swapped out (bytes)
	- Users: list all:
		- user
		- session started
		- host 
		- # processes running 
	- Processes (top): all, and by user. For each process, list:
		- PID 
		- name
		- user 
		- status 
		- created
		- RSS
		- VMS
		- Memory %
		- CPU %
		- # open files 
		- # connections 
		- # threads
		- **TODO: In the future could have much more detailed process listing
			(ex: see: https://raw.githubusercontent.com/Jahaja/psdash/master/docs/screenshots)
====================================================
"""

import os 
#import pwd
import json 
import platform

system = {}

# Basic distribution information 
distribution = platform.linux_distribution() # name, version, code name 
architecture = platform.architecture()	# bit architecture and executable format 
system['distribution'] = {'OS': platform.system(), 
						  'hostname': platform.node(), 
						  'release': platform.release(), 
						  'version': platform.version(), 
						  'machine': platform.machine(), 
						  'processor': platform.processor(),
						  'linux-distribution': distribution[0],
						  'linux-version': distribution[1],
						  'linux-codename': distribution[2],
						  'architecture': ','.join(list(platform.architecture()))}

# NOTE: 'lm' flag indicates true architecture -- could be running 32 bit kernel on 64 bit system 
# lm flag found in cpuinfo file? 

# Processors information 
processors = []
processor = {}
with open('/proc/cpuinfo') as cpulines:
	for line in cpulines:
		if not line.strip():
			processors.append(processor)
			processor = {}
		else:
			key, val = line.split(':')
			processor[key.strip()] = val.strip()
system['processors'] = processors 

# Memory information -- all information 
# Includes swap/dirty information
mem_info = {}
with open('/proc/meminfo') as memlines:
	for line in memlines:
		key, val = line.split(':')
		mem_info[key.strip()] = val.strip()
system['memory'] = mem_info 

# Use free for now just because it converts stuff for you! 
# free displays the total amount of free and used physical 
# and swap memory in the system, as well as the buffers 
# used by the kernel. Based on /proc/meminfo anyway.  
freelines = os.popen('free -tmo').read().splitlines()
mem, total_mem, used_mem, free_mem, shared_mem, buffer_mem, cached_mem = freelines[1].split()
swap, total_swap, used_swap, free_swap = freelines[2].split()
mem_info['quick'] = {'total-memory': total_mem,
					 'total-swap': total_swap,
					 'total-space': total_mem + total_swap,
					 'used-memory': used_mem,
					 'used-swap': used_swap,
					 'total-used': used_mem + used_swap,
					 'free-mem': free_mem,
					 'free-swap': free_swap,
					 'total-free': free_mem + free_swap,
					 'shared-memory': shared_mem,
					 'buffer-memory': buffer_mem,
					 'cached-memory': cached_mem}

# Processes - equivalent of top - either check in /proc/ or use top 
# /proc/<#s> ==> directory for each process named by pid 
# process_list = filter(lambda d: d.isdigit(), os.listdir('/proc')) 
top = os.popen('top -b -n1').read().splitlines()
uptime, _, num_users, ld_avg_1, ld_avg_2, ld_avg_3 = top[0].split(',')
uptime = ' '.join(uptime.split()[-2:])
num_users = int(num_users.strip().split()[0])
ld_avg_1 = float(ld_avg_1.split(':')[1].strip())
ld_avg_2 = float(ld_avg_2.strip())
ld_avg_3 = float(ld_avg_3.strip())
num_tasks, num_running, num_sleeping, num_stopped, num_zombie = [num.split()[1].strip() for num in top[1].split(',')]
user_cpu, sys_cpu, nice_cpu, idle_cpu, wait_cpu, hi_cpu, si_cpu, st_cpu = [float(perc.split('%')[0].strip()) for perc in top[2].split(':')[1].split(',')]
system['process_info'] = {
	'uptime': uptime,
	'num users': num_users,
	'load average 1': ld_avg_1,
	'load average 2': ld_avg_2,
	'load average 3': ld_avg_3,
	'tasks': {'total': num_tasks, 'running': num_running, 'sleeping': num_sleeping, 'stopped': num_stopped, 'zombie': num_zombie},
	'cpu': {'user': user_cpu, 'system': sys_cpu, 'nice': nice_cpu, 'idle': idle_cpu, 'IO wait': wait_cpu, 'HI': hi_cpu, 'SI': si_cpu, 'ST': st_cpu}
}
# Lines 3 and 4 already covered by free -tmo
# Process id, username, nice in range -20 to 20, virtual?, res_memory is current amount of process memory residing in physical memory (kb),
# shr, s, % of available cpu time used by this process, memory, number of cpu seconds the process has used, name of command running 
process_keys = ('pid', 'user', 'priority', 'nice', 'virtual', 'resident_memory', 'shr', 's', '%cpu', 'memory', 'time', 'command')
processes = {}
for pk in process_keys:
	processes[pk] = []
for line in top[7:]:
	process_vals = line.split()
	for i, val in enumerate(process_vals):
		processes[process_keys[i]].append(val.strip()) 
system['processes'] = processes 

# User information 
# print "\tUsers:"
# users = pwd.getpwpall()
# for user in users:
# 	print user.pw_name, ':', user.pw_shell
# Gets users that are online 
userlines = os.popen('w -h').read().splitlines()
users = {}
for line in userlines:
	# tty = terminal 
	# JCPU = time used by all processes attached to tty 
	# PCPU = time used by current process 
	# command = what = command of current process (ex: top, python)
	user, tty, remote_host, login_time, idle_time, jcpu, pcpu, command = line.split()
	user = user.strip()
	user_info = {'tty': tty.strip(), 
				 'host': remote_host.strip(),
				 'login time': login_time.strip(),
				 'idle time': idle_time.strip(),
				 'JCPU': jcpu.strip(),
				 'PCPU': pcpu.strip(),
				 'command': command.strip()
				 }
	try:
		users[user].append(user_info)
	except KeyError:
		users[user] = [user_info]

system['users'] = users 

fname = system['distribution']['hostname'] + '.json'
json.dump(system, open('/home/ndg/project/users/mciot/dashboard/' + fname, 'w'), indent=4)

#### TODO ####
# Network information 
#netlines = open('/proc/net/dev').read().splitlines()

# Block devices 



# /proc/uptime 

