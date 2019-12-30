from SETprefixLimit import findMaxPrefix
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
import paramiko
import threading
os.sys.path.append('/home/gardusi/github/sql_library/')
#from sql_json import mySQL

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

  def build_documents(self):
    max_prefix = findMaxPrefix(self.ips, self.credentials['username'], self.credentials['password'], self.timeout)
    print(max_prefix)
    documents = []
    for ip in self.ips:
      for peer in self.ips[ip]['peers']:
        for route in self.ips[ip]['peers'][peer]['routes']:

          try:
            cur_prefix = 0
            cur_group = self.ips[ip]['peers'][peer]['group']
            if ip in max_prefix:
              if cur_group in max_prefix[ip]:
                cur_prefix = max_prefix[ip][cur_group]
              if peer in max_prefix[ip]:
                cur_prefix = max_prefix[ip][peer]
          except:
               print(f"ip: {ip}")
               print(f"peer: {peer}")
               print(f"cur_group: {cur_group}")

          try:
              documents.append({
                'last_up_down': self.ips[ip]['peers'][peer]['last_up_down'],
                'ip': ip,
                'hostname': self.ips[ip]['hostname'],
                'peer': peer,
                'status': self.ips[ip]['peers'][peer]['status'],
                'routing_table': route,
                'active': self.ips[ip]['peers'][peer]['routes'][route]['active'],
                'received': self.ips[ip]['peers'][peer]['routes'][route]['received'],
                'accepted': self.ips[ip]['peers'][peer]['routes'][route]['accepted'],
                'dump': self.ips[ip]['peers'][peer]['routes'][route]['dump'],
                'advertised': self.ips[ip]['peers'][peer]['routes'][route]['advertised'],
                'as': self.ips[ip]['peers'][peer]['as'],
                'contact': '?',
                'threshold': '?',
                'date': date,
                'group': self.ips[ip]['peers'][peer]['group'],
                'description': self.ips[ip]['peers'][peer]['description'],
                'max_prefix': cur_prefix,
              })

          except Exception as e:
              print(f"excecao: {e}")
              print(f"ip: {ip}")
              print(f"peer: {peer}")
              print(self.ips[ip]['peers'])

    return documents

  def get_neighbor(self, ip):
    commands = []
    for peer in self.ips[ip]['peers']:
      commands.append('show bgp neighbor' + ' ' + str(peer))
    return self.remote_access_run(ip, commands)

  def get_neighbors(self):
    jobs = []
    for ip in self.ips:
      jobs.append([
        self.get_neighbor,
        ip
      ])
    results = multi_threaded_execution(jobs)
    for ip, result in zip(self.ips, results):
        print("esse eh um ip: ------------")
        print(ip)
        print("esse eh um result:  -------")
        print(result)
    for ip, result in zip(self.ips, results):
      if result == None:
        continue
      current_peer = -1
      current_route = "kkk"
      peers = list(self.ips[ip]['peers'].keys())
      print("esse sao os peers: ----------------------------------------")
      print(f"meu ip: {ip}")
      print(peers)
      for line in result:
        print(line)
        if line.find('Peer:') != -1:
          current_peer += 1
          if current_peer < len(peers):
            self.ips[ip]['peers'][peers[current_peer]]['description'] = '???'
            self.ips[ip]['peers'][peers[current_peer]]['group'] = '???'
            print(f"defini {peers[current_peer]} com a description = ???")
            print(f"defini {peers[current_peer]} com o group = ???")
          else:
            break

        elif line.find('Description: ') != -1:
          print(f"defini {peers[current_peer]} com a description = {line.strip()}")
          self.ips[ip]['peers'][peers[current_peer]]['description'] = line.strip()[13:]

        elif line.find('Group: ') != -1:
          print(f"defini {peers[current_peer]} com o group = {line.strip()}")
          self.ips[ip]['peers'][peers[current_peer]]['group'] = line.strip()[7:line.strip().find("Routing-Instance")].strip()

        elif line.find('Table') != -1:
          current_route = line.strip().split(' ')[1]

        elif line.find('Advertised prefixes: ') != -1:
          if current_route not in self.ips[ip]['peers'][peers[current_peer]]['routes']:
              self.ips[ip]['peers'][peers[current_peer]]['routes'][current_route] = { 'advertised' : '???' }
          self.ips[ip]['peers'][peers[current_peer]]['routes'][current_route]['advertised'] = line.strip().split(' ')[-1]
          print(self.ips[ip]['peers'][peers[current_peer]]['routes'][current_route]['advertised'])


  def get_peer(self, ip):
    return self.remote_access_run(
      ip,
      [
        'show bgp summary'
      ]
    )

  def get_peers(self, ips):
    jobs = []
    for ip in ips:
      jobs.append([
        self.get_peer,
        ip
      ])
    self.ips = {}
    results = multi_threaded_execution(jobs)
    for ip, result in zip(ips, results):
      self.ips[ip] = {}
      self.ips[ip]['hostname'] = ips[ip]
      self.ips[ip]['peers'] = {}
      if result == None:
        continue
      flag = False
      for line in result:
        v = list(filter(None, line.strip().split(' ')))
        if len(v) == 0:
          continue
        if v[0][0].isdigit() == True:
          for i in range(len(v) - 1, -1, -1):
            for current_status in self.status:
              if v[i].find(current_status) != -1:
                peer = v[0]
                self.ips[ip]['peers'][peer] = {
                  'routes': {},
                  'status': current_status,
                  'last_up_down': v[i - 2] + ' ' + v[i - 1],
                  'as': v[1],
                }
                if current_status == 'Establ':
                  flag = True
                else:
                  self.ips[ip]['peers'][peer]['routes']['?'] = {
                    'active': 0,
                    'received': 0,
                    'accepted': 0,
                    'dump': 0,
                    'advertised': 0,
                  }
                break
        elif flag == True:
          routes = v[1].split('/')
          self.ips[ip]['peers'][peer]['routes'][v[0][:-1]] = {
            'active': routes[0],
            'received': routes[1],
            'accepted': routes[2],
            'dump': routes[3],
          }

  def remote_access_run(self, ip, commands):
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
          ans = []
          for command in commands:
            with ssh.invoke_shell() as channel:
              stdin, stdout, stderr = ssh.exec_command(
                command,
                timeout = self.timeout,
              )
            for line in stdout.readlines():
              ans.append(line)
          return ans
        except Exception as exception:
          with lock:
            allowed = False
            s = str(exception)
            print(ip, file = os.sys.stderr)
            print(exception, file = os.sys.stderr)
            print(s, file = os.sys.stderr)
            for error in self.allowed_errors:
              if s.find(error) != -1:
                allowed = True
                break
            if allowed == False:
              return None

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
  user.get_peers(ips)
  user.get_neighbors()
  docs = user.build_documents()
  print(docs)
  for x in docs:
      print(x)

  # insert_documents(
  #   docs,
  #   read_json(config['database_credentials_filepath']),
  #   config['database_name'],
  #   config['table_name'],
  #   read_json(current_filepath + 'table_info.json')
  # )

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
