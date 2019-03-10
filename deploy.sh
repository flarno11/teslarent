#!/bin/bash

scp *.py *.sh *.conf requirements.txt prometheus:./teslaRent/
scp static/* prometheus:./solarViz/static/
ssh prometheus -o "ClearAllForwardings yes" "sudo systemctl restart teslaRent"

#python3 -m venv venv
#source venv/bin/activate
#pip install --upgrade pip  # important! otherwise there are errors like "error: invalid command 'bdist_wheel'"
#pip install -r requirements.txt
