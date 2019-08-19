#!/usr/bin/python3
# -*- coding: utf-8 -*-
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#         OS : GNU/Linux Ubuntu 16.04 or 18.04
#   LANGUAGE : Python 3.5.2 or later
#     AUTHOR : Kornilova D. V.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

'''
    Клиент отправляет запросы с помощью библиотеки requests и ждет отклика серверва. 
    Клиент получает информация про наш веб-сервер, а далее отсылает 10 сообщений 
    с текстом iter n, чтобы перейти на следующую итерацию n+1, клиент должен 
    дождаться отклика сервера, n - номер итерации.'''

import sys
import re
import subprocess
import base64

import requests


def get_addr(host):
    ''' 
    Определение адрес машины.Если на входе 'localaddr', то определяет адрес 
    машины в локальной сети с помощью утилиты 'ifconfig' из пакета net-tools.
    
    Аргументы:
    host - адрес
    '''
    if host == 'localaddr':
        command_line = 'ifconfig'
        proc = subprocess.Popen(command_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        out = out.decode()
        inet = re.findall(r'inet \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', out)
        addr = '127.0.0.1'
        for i in range(len(inet)):
            if inet[i][5:8] == '192':
                local_addr = inet[i][5:]
                break
            elif inet[i][5:8] == '172':
                local_addr = inet[i][5:]
    elif host.count('.') == 3:
        return host
    else:
        print("\n[E] Неверный аргумент командной строки host:port.")
   
try:
    host, port = sys.argv[1].split(':')
    host = get_addr(host)
except:
    host = '192.168.2.58'
    port = '5000'

login = 'test_serv'
password = 'task_4'
login_password = login + ':' + password

url = 'http://' + host + ':' + port + '/'

auth = base64.b64encode(login_password.encode())
headers = {'Content-Type': 'application/json',
           'Authorization': 'Basic ' + auth.decode()}

result = requests.get(url + 'about', headers=headers, verify=False)
data = result.json()
data = data.get('text')
print('[i] Получено сообщение: %s' % data)

i = 1
while i < 10:
    data = {'text': 'iter  ' + str(i)}
    result = requests.post(url, headers=headers, json=data, verify=False, allow_redirects=True)
    data = result.json()
    print('[i] Получено сообщение: %s' % data.get('text'))
    i += 1
