#!/bin/bash

CORES=$(nproc)

echo "CPU Cores: $CORES"

for i in $(seq 1 $CORES)
do
    while :; do :; done &
done

echo "CPU stress started."
echo "Use 'pkill -f cpu-load.sh' or 'killall bash' (carefully) to stop."
wait
