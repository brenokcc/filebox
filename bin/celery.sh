#!/usr/bin/env bash
cd "$( cd "$(dirname "$0")" ; cd .. ; pwd -P )" || exit
celery -A filebox worker -l INFO -Q geral