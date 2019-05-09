from concurrent.futures import ThreadPoolExecutor
import json
import paramiko
import threading

lock = threading.Lock()

def main():
  config = read_json('config.json')
  ips = read_json(config['ips_filepath'])
  credentials = read_json(config['credentials_filepath'])

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

def remote_access_run(ip, command, credentials):
  allowed_errors = [
    '[Errno 104] Connection reset by peer',
  ]
  timeout = 32
  remaining_attempts = 64
  while remaining_attempts > 0:
    remaining_attempts -= 1
    with paramiko.SSHClient() as ssh:
      try:
        # paramiko.common.logging.basicConfig(level = paramiko.common.DEBUG)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
          ip,
          username = credentials['username'],
          password = credentials['password'],
          auth_timeout = timeout,
          banner_timeout = timeout,
          timeout = timeout,
        )
        stdin, stdout, stderr = ssh.exec_command(
          command,
          timeout = timeout
        )
        ans = []
        for line in stdout.readlines():
          ans.append(line)
        return ans
      except Exception as exception:
        allowed = False
        s = str(exception)
        with lock:
          print(ip, file = sys.stderr)
          print(exception, file = sys.stderr)
        for error in allowed_errors:
          if s.find(error) != -1:
            allowed = True
            break
        if allowed == False:
          return None

main()