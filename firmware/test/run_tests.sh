#!/bin/sh
# Compila ed esegue i test host
set -e
cd "$(dirname "$0")"
make test
