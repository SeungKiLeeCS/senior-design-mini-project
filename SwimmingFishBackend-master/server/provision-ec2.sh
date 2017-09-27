#!/usr/bin/env bash

sudo apt-get update
sudo apt-get install python3-pip
sudo apt-get install python-dev libmysqlclient-dev
sudo pip3 install mysqlclient
sudo pip3 install django


sudo apt-get install apache2 apache2-dev -y

wget https://github.com/GrahamDumpleton/mod_wsgi/archive/4.5.17.tar.gz
mv 4.5.17.tar.gz mod_wsgi-4.5.17.tar.gz
tar xvfz mod_wsgi-4.5.17.tar.gz
cd mod_wsgi-4.5.17/
./configure --with-python=/usr/bin/python3
make
sudo make install

