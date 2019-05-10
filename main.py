from concurrent.futures import ThreadPoolExecutor
import json
from os import sys
import paramiko
import threading

lock = threading.Lock()

class User:
  allowed_errors = [
    '[Errno 104] Connection reset by peer',
  ]
  attempts = 32
  timeout = 32
  not_established = [
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
      ans[ip]['peers'] = []
      if result == None:
        continue
      flag = False
      for line in result:
        v = list(filter(None, line.strip().split(' ')))
        if flag == True and len(v) > 0 and v[0][0].isdigit() == True:
          status = 'Establ'
          for bad_status in self.not_established:
            for i in range(len(v) - 1, -1, -1):
              if v[i].find(bad_status) != -1:
                status = bad_status
          ans[ip]['peers'].append({
            'peer': v[0],
            'status': status
          })
        elif flag == True:
          print(v)
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
            print(ip, file = sys.stderr)
            print(exception, file = sys.stderr)
            for error in self.allowed_errors:
              if s.find(error) != -1:
                allowed = True
                break
            if allowed == False:
              return None

def main():
  config = read_json('config.json')
  ips = read_json(config['ips_filepath'])
  user = User(config['credentials_filepath'])
  ips = user.get_peers(ips)
  for ip in ips:
    print('ip: ' + ip + ', hostname: ' + ips[ip]['hostname'])
    print('peers: ' + str(ips[ip]['peers']))

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