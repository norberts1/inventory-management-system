#!/bin/bash
#
cd ./inventory
# running on; port:5000 and for host:all public IPs
#  change 'port'-number if required and 'host'-IP to open flask only for know host's
python3 -m flask run --port=5000 --host=0.0.0.0
