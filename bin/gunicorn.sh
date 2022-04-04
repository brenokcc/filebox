#!/usr/bin/env bash
cd "$( cd "$(dirname "$0")" ; cd .. ; pwd -P )" || exit
gunicorn -b 0.0.0.0:80 filebox.wsgi:application -w 1 -t 360