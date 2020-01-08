# Transport

Note:


Existe um problema na biblioteca paramiko pois ela não permite o recebimento de caracteres fora do padrão utf-8, para ignorar esses caracteres e resolver momentaneamente o problema acesse o diretório base da sua instalação do python no seu virtual enviroment:
(No meu caso, esse diretório está nomeado como '/venv')

Edite o arquivo "/venv/lib/python3.6/site-packages/paramiko/py3compat.py"


Altere as linhas 64 e 68 do arquivo de "return s.decode(encoding)" para "return s.decode(encoding, 'ignore')"

