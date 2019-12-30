import paramiko
import json
import pprint

def read_json(filepath):
  with open(filepath, 'rb') as file:
    return json.load(file, encoding = 'utf-8')

def findMaxPrefix(ips, username, password, timeout):
    prefix_info = {}
    with paramiko.SSHClient() as ssh:
        try:

            #paramiko.common.logging.basicConfig(level = paramiko.common.DEBUG)
            for ip in ips:
                print(ip)
                prefix_info[ip] = {}
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                  ip,
                  username = username,
                  password = password,
                  auth_timeout = timeout,
                  banner_timeout = timeout,
                  timeout = timeout,
                )

                stdin, stdout, stderr = ssh.exec_command(
                  "show configuration protocols bgp | display set | grep \"prefix-limit maximum\"",
                  timeout = timeout,
                )

                for line in stdout.readlines():
                    print(line, end = "")

                    line = line.split(" ")
                    for i in range(0, len(line)):
                        if line[i] == "neighbor":
                            prefix_info[ip][ line[i+1] ] = int(line[-1])
                            break
                    else:
                        for i in range(0, len(line)):
                            if line[i] == "group":
                                prefix_info[ip][ line[i+1] ] = int(line[-1])
            return prefix_info


        except Exception as e:
            print("something happened")
            print(e)
            pass

    return(ans)


if __name__ == "__main__":
    max_prefix = findMaxPrefix( read_json("ips.json"), "northstar", "LsP$Cap*2018", 32)
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(max_prefix)
