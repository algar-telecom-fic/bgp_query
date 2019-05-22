from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
import paramiko
import threading
os.sys.path.append('/home/gardusi/github/sql_library/')
from sql_json import mySQL

date = datetime.datetime.now()
current_filepath = os.path.realpath(
  os.path.join(os.getcwd(), os.path.dirname(__file__))
) + '/'
lock = threading.Lock()

class User:
  allowed_errors = [
    '[Errno 104] Connection reset by peer',
  ]
  attempts = 32
  timeout = 32
  status = [
    'Establ',
    'Active',
    'Connect',
    'Idle',
  ]

  def __init__(self, filepath):
    self.credentials = read_json(filepath)

  def get_peer(self, ip):
    return self.remote_access_run(
      ip,
      'show bgp summary'
    )

  def get_peers(self, ips):
    jobs = []
    for ip in ips:
      jobs.append([
        self.get_peer,
        ip
      ])
    ans = {}
    results = multi_threaded_execution(jobs)
    for ip, result in zip(ips, results):
      ans[ip] = {}
      ans[ip]['hostname'] = ips[ip]
      ans[ip]['peers'] = {}
      if result == None:
        continue
      flag = False
      for line in result:
        v = list(filter(None, line.strip().split(' ')))
        if flag == True and len(v) > 0 and v[0][0].isdigit() == True:
          for i in range(len(v) - 1, -1, -1):
            for current_status in self.status:  
              if v[i].find(current_status) != -1:
                peer = v[0]
                ans[ip]['peers'][peer] = {
                  'routes': {},
                  'status': current_status,
                  'up_down': v[i - 1],
                  'last': v[i - 2],
                }
                break
        elif flag == True:
          routes = v[1].split('/')
          ans[ip]['peers'][peer]['routes'][v[0][:-1]] = {
            'active': routes[0],
            'received': routes[1],
            'accepted': routes[2],
            'dump': routes[3],
          }
        elif len(v) > 0 and v[0] == 'Peer':
          flag = True
    return ans

  def remote_access_run(self, ip, command):
    for attempt in range(self.attempts):
      with paramiko.SSHClient() as ssh:
        try:
          # paramiko.common.logging.basicConfig(level = paramiko.common.DEBUG)
          ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
          ssh.connect(
            ip,
            username = self.credentials['username'],
            password = self.credentials['password'],
            auth_timeout = self.timeout,
            banner_timeout = self.timeout,
            timeout = self.timeout,
          )
          stdin, stdout, stderr = ssh.exec_command(
            command,
            timeout = self.timeout,
          )
          ans = []
          for line in stdout.readlines():
            ans.append(line)
          return ans
        except Exception as exception:
          with lock:
            allowed = False
            s = str(exception)
            print(ip, file = os.sys.stderr)
            print(exception, file = os.sys.stderr)
            for error in self.allowed_errors:
              if s.find(error) != -1:
                allowed = True
                break
            if allowed == False:
              return None

def build_documents(ips):
  documents = []
  for ip in ips:
    for peer in ips[ip]['peers']:
      for route in ips[ip]['peers'][peer]['routes']:
        documents.append({
          'up_down': ans[ip]['peers'][peer]['up_down'],
          'last': ans[ip]['peers'][peer]['last'],
          'ip': ip,
          'hostname': ips[ip]['hostname'],
          'peer': peer,
          'status': ips[ip]['peers'][peer]['status'],
          'routing_table': route,
          'active': ips[ip]['peers'][peer]['routes'][route]['active'],
          'received': ips[ip]['peers'][peer]['routes'][route]['received'],
          'accepted': ips[ip]['peers'][peer]['routes'][route]['accepted'],
          'dump': ips[ip]['peers'][peer]['routes'][route]['dump'],
          'date': date,
        })
  return documents

def insert_documents(documents, database_credentials, database_name, table_name, table_info):
  db = mySQL(
    database_credentials = database_credentials,
    database_name = database_name,
  )
  db.create_table(
    table_info = table_info,
    table_name = table_name,
  )
  db.insert_into(
    table_info = table_info,
    table_name = table_name,
    values = documents,
  )

def main():
  config = read_json(current_filepath + 'config.json')
  ips = read_json(config['ips_filepath'])
  user = User(config['credentials_filepath'])
  ips = user.get_peers(ips)
  documents = build_documents(ips)
  database_credentials = read_json(config['database_credentials_filepath'])
  database_name = config['database_name']
  table_name = config['table_name']
  table_info = read_json(current_filepath + 'table_info.json')
  insert_documents(documents, database_credentials, database_name, table_name, table_info)

def multi_threaded_execution(jobs, workers = 256):
  ans = []
  threads = []
  with ThreadPoolExecutor(max_workers = workers) as executor:
    for parameters in jobs:
      threads.append(
        executor.submit(
          parameters[0],
          *parameters[1:]
        )
      )
  for thread in threads:
    ans.append(thread.result())
  return ans

def read_json(filepath):
  with open(filepath, 'rb') as file:
    return json.load(file, encoding = 'utf-8')

main()
