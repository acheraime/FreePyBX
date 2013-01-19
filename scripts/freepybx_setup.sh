#!/bin/sh

if [ -e /usr/local/www/bin/activate ]; then
        . /usr/local/www/bin/activate
fi

cd /usr/local/www/FreePyBX
python setup.py develop
