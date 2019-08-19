#!/usr/bin/python3
# -*- coding: utf-8 -*-
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#         OS : GNU/Linux Ubuntu 16.04 or 18.04
#   LANGUAGE : Python 3.5.2 or later
#     AUTHOR : Kornilova D. V.
# MAINTAINER : Klim V. O.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

'''REST - сервер. С использвоанием Flask и WSGIServer.'''

import re
import os
import sys
import socket
import subprocess
import signal
import platform
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
import socketserver

from flask import Flask, jsonify, make_response, request, __version__ as flask_version
from flask_httpauth import HTTPBasicAuth
from gevent import __version__ as wsgi_version
from gevent.pywsgi import WSGIServer


# Создание папки для логов, если она была удалена
if not os.path.exists('log'):
    os.makedirs('log')

app = Flask(__name__)
auth = HTTPBasicAuth()

login = 'test_serv'
password = 'task_4'
max_content_length = 16 * 1024 * 1024


@auth.get_password
def get_password(username):
    if username == login:
        return password


# Создание логов
#logging.basicConfig(filename='sample.log',level=logging.INFO,format='%(levelname)-8s | %(asctime)s - %(message)s')
logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)
# для записи в файл
fh = RotatingFileHandler(
    'log/server.log', maxBytes=16 * 1024 * 1024, backupCount=5)
fh.setLevel(logging.DEBUG)
# для вывода на консоль
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# задаем формат
formatter = logging.Formatter('%(levelname)-8s | %(asctime)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
# добавляем
logger.addHandler(ch)
logger.addHandler(fh)


def log(message, addr=None, level='info'):
    ''' Запись сообщения в лог файл с уровнем INFO или ERROR. По умолчанию используется INFO.'''
    if level == 'info':
        if addr is None:
            logger.info(' ' + message)
        else:
            logger.info('-addr - ' + addr + '   ' + message)
    elif level == 'error':
        if addr is None:
            logger.error(' ' + message)
        else:
            logger.error('-addr - ' + addr + '   ' + message)

# Переопределение ошибок
@app.errorhandler(400)
def request_body(error):
    return make_response(jsonify({'error': 'The request body contains no data.'}), 400)


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access.'}), 401)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'The requested URL was not found on the server.'}), 404)


@app.errorhandler(405)
def method_not_allowed(error):
    return make_response(jsonify({'error': 'The method is not allowed for the requested URL.'}), 405)


@app.errorhandler(406)
def acceptablee(error):
    return make_response(jsonify({'error': ' Not Acceptable'}), 406)


@app.errorhandler(500)
def internal_server_error(error):
    print(error)
    return make_response(jsonify({'error': 'The server encountered an internal error and was unable to complete your request.'}), 500)


def limit_content_length(f):
    ''' Декоратор для ограничения размера передаваемых клиентом данных. '''
    def decorator():
        if request.content_length > max_content_length:
            log('превышен максимальный размер передаваемых данных ({:.2f} кБ)'.format(
                request.content_length/1024), request.remote_addr, 'error')
            return make_response(jsonify({'error': 'Maximum data transfer size exceeded, allowed only until {: .2f} kB.'.format(max_content_length/1024)}), 413)
        return f()
    return decorator


@app.route('/about', methods=['GET'])
@auth.login_required
def info_server():
    return jsonify({'text': 'Сервер соответствующий архитектуре REST.В зависимоти от входных параметров сервер будет запускать либо тестовый flask сервер, либо WSGI сервер.\n' +
                    'Также имеется ограничение на размер принимаемых данных в теле запроса равное 16 Мб.Поддерживает https с сертификатами от openssl.Любой обмен данными с клиентами осуществляется с помощью json.Сервер имеет базовую http-авторизацию.\n' +
                    'Все действия на всех уровнях заносятся в log (формат логов: уровень | адрес_клиента, сообщение, log дублируется в терминале'})


@app.route("/", methods=['POST'])
@auth.login_required
@limit_content_length
def send_response():
    data = request.json
    data = data.get('text')
    if data is None:
        log('json в теле запроса имеет неправильную структуру',
            request.remote_addr, 'error')
        return make_response(jsonify({'error': 'Json in the request body has an invalid structure.'}), 415)
    log('принято: "' + data + '"', request.remote_addr)
    return jsonify({'text': 'OK'})


def get_localaddr(host):
    ''' 
    Определение адреса машины в локальной сети с помощью утилиты 'ifconfig' из пакета net-tools.
    '''
    if host == 'localaddr':
        command_line = 'ifconfig'
        proc = subprocess.Popen(command_line, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        out = out.decode()
        inet = re.findall(
            r'inet \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', out)
        addr = '127.0.0.1'
        for i in range(len(inet)):
            if inet[i][5:8] == '192':
                local_addr = inet[i][5:]
                break
            elif inet[i][5:8] == '172':
                local_addr = inet[i][5:]
        return str(local_addr)
    elif host.count('.') == 3:
        return host
    else:
        print(
            "\n[E] Неверный аргумент командной строки host:port. Введите help для помощи.\n")


def get_free_port(host, port):
    ''' Автовыбор доступного порта (если указан порт 0)'''
    if int(port) == 0:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((host, 0))
            port = sock.getsockname()[1]
            print('выбран порт ' + str(port))
            sock.close()
        except socket.gaierror:
            print('адрес ' + host + ':' + str(port) +
                  ' некорректен', level='error')
            sock.close()
            return
        except OSError:
            print('адрес ' + host + ':' + str(port) +
                  ' недоступен', level='error')
            sock.close()
            return
    else:
        return int(port)


def run(host, port, wsgi=False, https=False):
    '''Запуск сервера    

    Аргументы
    host - адрес на котором будет запущен сервер
    port - порт на котором будет запущен сервер
    wsgi - True: запуск WSGI сервера, False: запуск тестового Flask сервера
    https - True: запуск в режиме https (сертификат и ключ должны быть в cert.pem и key.pem), False: запуск в режиме http
    '''
    log('Flask v.' + flask_version + ', WSGIServer v.' + wsgi_version)
    log('установлен максимальный размер принимаемых данных: {:.2f} Кб'.format(
        max_content_length/1024))

    if wsgi:
        global http_server
        try:
            if https:
                log('WSGI запущен на https://' + host + ':' +
                    str(port) + ' (нажмите Ctrl+C или Ctrl+Z для выхода)')
                http_server = WSGIServer(
                    (host, port), app, log=logger, error_log=logger, keyfile='key.pem', certfile='cert.pem')
            else:
                log('WSGI сервер запущен на http://' + host + ':' +
                    str(port) + ' (нажмите Ctrl+C или Ctrl+Z для выхода)')
                http_server = WSGIServer(
                    (host, port), app, log=logger, error_log=logger)
            http_server.serve_forever()
        except OSError:
            print()
            log('адрес ' + host + ':' + str(port) + ' недоступен', level='error')
    else:
        log('запуск тестового Flask сервера...')
        try:
            if https:
                app.run(host=host, port=port, ssl_context=(
                    'cert.pem', 'key.pem'), threaded=True, debug=False)
            else:
                app.run(host=host, port=port, threaded=True, debug=False)
        except OSError:
            print()
            log('адрес ' + host + ':' + str(port) + ' недоступен', level='error')




def main():
    host = '127.0.0.1'
    port = 5000
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '-s':
            if len(sys.argv) > 2:
                if sys.argv[2] == '-d':
                    if len(sys.argv) > 3:
                        if sys.argv[3].count(':') == 1:
                            hostport = re.split(':', sys.argv[3])
                            host, port = hostport
                            host = get_localaddr(host)
                            port = get_free_port(host, port)
                            run(host, port, https=True)
                        else:
                            print("\n[E] Неверный аргумент командной строки '" +
                                  sys.argv[3] + "'. Введите help для помощи.\n")
                    else:
                        run(host, port, https=True)
                elif sys.argv[2].count(':') == 1:
                    host, port = re.split(':', sys.argv[2])
                    host = get_localaddr(host)
                    port = get_free_port(host, port)
                    run(host, port, wsgi=True, https=True)
                else:
                    print("\n[E] Неверный аргумент командной строки '" +
                          sys.argv[2] + "'. Введите help для помощи.\n")
            else:
                host = get_localaddr('localaddr')
                port = get_free_port(host, port)
                run(host, port, wsgi=True, https=True)
                # -s - запуск WSGI сервера с поддержкой https, автоопределением адреса машины в	локальной сети и портом 5000.
        elif sys.argv[1] == '-d':
            if len(sys.argv) > 2:
                if sys.argv[2].count(':') == 1:
                    host, port = re.split(':', sys.argv[2])
                    host = get_localaddr(host)
                    port = get_free_port(host, port)
                    run(host, port, wsgi=True)
                else:
                    print("\n[E] Неверный аргумент командной строки '" +
                          sys.argv[2] + "'. Введите help для помощи.\n")
            else:
                run(host, port)
        elif sys.argv[1].count(':') == 1:
            host, port = re.split(':', sys.argv[1])
            host = get_localaddr(host)
            port = get_free_port(host, port)
            run(host, port, wsgi=True)
        elif sys.argv[1] == 'help':
            print('\nВозможные варианты :')
            print('\tбез аргументов - запуск WSGI сервера с автоопределением адреса машины в локальной сети и портом 5000')
            print('\thost:port - запуск WSGI сервера на host:port')
            print('\t-d - запуск тестового Flask сервера на 127.0.0.1:5000')
            print('\t-d host:port - запуск тестового Flask сервера на host:port')
            print('\t-d localaddr:port - запуск тестового Flask сервера с автоопределением адреса машины в локальной сети и портом port')
            print('\t-s - запуск WSGI сервера с поддержкой https, автоопределением адреса машины в локальной сети и портом 5000')
            print('\t-s host:port - запуск WSGI сервера с поддержкой https на host:port')
            print(
                '\t-s -d - запуск тестового Flask сервера с поддержкой https на 127.0.0.1:5000')
            print(
                '\t-s -d host:port - запуск тестового Flask сервера с поддержкой https на host:port')
            print('\t-s -d localaddr:port - запуск тестового Flask сервера с поддержкой https, автоопределением адреса машины в локальной сети и портом port\n')
        else:
            print("\n[E] Неверный аргумент командной строки '" +
                  sys.argv[1] + "'. Введите help для помощи.\n")
    else:
        host = get_localaddr('localaddr')
        run(host, port, wsgi=True)


def on_stop(*args):
    print()
    log('сервер остановлен')
    if http_server != None:
        http_server.close()
    sys.exit(0)


if __name__ == '__main__':
    # При нажатии комбинаций Ctrl+Z, Ctrl+C либо закрытии терминала будет вызываться функция on_stop() (Работает только на linux системах!)
    if platform.system() == 'Linux':
        for sig in (signal.SIGTSTP, signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, on_stop)
    main()
