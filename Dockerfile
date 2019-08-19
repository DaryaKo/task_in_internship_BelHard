FROM ubuntu:18.04
MAINTAINER Kornilova Darya 'kodavidav@gmail.com'

# Установка необходимых пакетов для Ubuntu
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && \
    apt-get install --fix-missing -y tzdata python3.6 python3-pip git locales net-tools

# Установка часового пояса хост-машины
ENV TZ=Europe/Minsk
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

# Установка модулей для Python3
RUN pip3 install --upgrade pip 
RUN pip3 install decorator==4.4.0 flask==1.0.3 flask-httpauth==3.2.4 gevent==1.4.0 requests==2.22.0 

# Копирование файлов проекта
COPY . /z4/
WORKDIR /z4/

# Изменение локализации для вывода кириллицы в терминале
RUN locale-gen en_US.UTF-8 
ENV LANG=en_US.UTF-8 
ENV LANGUAGE=en_US:en 
ENV LC_ALL=en_US.UTF-8

# Очистка кеша
RUN apt-get -y autoremove && \
    apt-get -y autoclean && \
    apt-get -y clean

CMD ["python3", "rest_server.py"]
