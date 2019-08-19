#!/bin/bash
apt-get -y update

# Установка пакетов Ubuntu
apt-get -y install python3.6 python3-pip git net-tools

# Установка пакетов Python3
yes | pip3 install --upgrade pip
yes | pip3 install decorator==4.4.0 flask==1.0.3 flask-httpauth==3.2.4 gevent==1.4.0 requests==2.22.0 

# Очистка кеша
apt-get -y autoremove
apt-get -y autoclean
apt-get -y clean
