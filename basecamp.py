"""
Gets basecamp information and saves it to JSON. 
Also, the beginning of a Python basecamp API wrapper? 

TODO: Will need to use API key in the future: https://github.com/basecamp/bcx-api
	  so that everyone can access this. https://github.com/basecamp/api/blob/master/sections/authentication.md
TODO: Store project ids to avoid extra API calls.
TODO: Store last-seen events so that can create notification system. 
"""

import json 
import requests 
from datetime import datetime 
from requests.auth import HTTPBasicAuth

credentials = open('sensitive.txt').read().splitlines()
username = credentials[0].strip()
password = credentials[1].strip()

today = datetime.today()

projects_url = 'https://basecamp.com/1930416/api/v1/projects.json'
def project_url(pid): return projects_url.replace('projects', 'projects/' + str(pid))
def todo_list_url(pid): return projects_url.replace('projects', 'projects/' + str(pid) + '/todolists')
def todo_url(pid, tid): return projects_url.replace('projects', 'projects/' + str(pid) + '/todolists/' + str(tid))
def discussion_url(pid): return projects_url.replace('projects', 'projects/' + str(pid) + '/topics')
def comment_url(pid, cid): return projects_url.replace('projects', 'projects/' + str(pid) + '/messages/' + str(cid))
def timestamp(datestr): return datetime.strptime(datestr.split('.')[0].strip(), '%Y-%m-%dT%H:%M:%S')
def fromToday(datestr): return (((today - timestamp(datestr)).seconds) / 3600) <= 24

auth = HTTPBasicAuth(username, password)
session = requests.Session()

# Get project information 
project_stuff = session.get(projects_url, auth=auth)
projects = json.loads(project_stuff.text)

# For each project, get all to dos that are due, and any comments 
# posted today. 
todos = {}
discussions = {}
for project in projects:
	pid = project['id']
	pname = project['name']
	tds = session.get(todo_list_url(pid), auth=auth).text
	tps = session.get(discussion_url(pid), auth=auth).text

	tds_json = json.loads(tds)
	tps_json = json.loads(tps)

	todos[pname] = {}
	discussions[pname] = {}

	# Go through each to do list 
	for tdlist in tds_json:
		tdid = tdlist['id']
		tdname = tdlist['name']

		todos[pname][tdname] = []

		td_stuff = session.get(todo_url(pid, tdid), auth=auth)
		todo_jsons = json.loads(td_stuff.text)['todos']['remaining']
		# Save the name and due date of the to do in the list 
		for todo in todo_jsons:
			todos[pname][tdname].append((todo['content'], todo['due_on']))

	# Collect discussions that have been active in the past 24 hours 
	for tplist in tps_json:		
		if fromToday(tplist['updated_at']):
			tpid = tplist['id']
			tpname = tplist['title']

			discussions[pname][tpname] = []
			
			comments_stuff = session.get(comment_url(pid, tpid), auth=auth)
			try:
				comments_json = json.loads(comments_stuff.text)['comments']
			except ValueError:
				#print 'moved?'
				continue

			print comment_url(pid, tpid)
			for comment in comments_json:
				if fromToday(comment['updated_at']):
					discussions[pname][tpname].append((comment['content'], comment['updated_at']))
				# Too old 
				else:
					break
		# Everything beyond this is too old, so stop
		# (assumes chronological ordering, which seems to be the case)
		else:
			break

basecamp = {'todos': todos, 'discussions': discussions}
json.dump(basecamp, open('basecamp_info.json', 'w'), indent=4)
