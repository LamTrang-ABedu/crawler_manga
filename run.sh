#!/bin/bash
cd /opt/hopehub/crawler_manga
git pull
pip3 install -r requirements.txt
pkill -f "5005"
# Chạy Flask app
/usr/bin/python3 app.py