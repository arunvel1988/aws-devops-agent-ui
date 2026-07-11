#!/bin/bash

echo "========================================"
echo "      CPU Load Generator for EC2"
echo "========================================"

# Check if stress is installed
if ! command -v stress >/dev/null 2>&1; then
    echo "Installing stress..."
    sudo apt update
    sudo apt install -y stress
fi

echo
echo "Number of CPU cores available:"
nproc

echo
read -p "Enter number of CPU workers: " CPU

read -p "Enter duration (seconds): " TIME

echo
echo "========================================"
echo "Generating CPU Load..."
echo "CPU Workers : $CPU"
echo "Duration    : $TIME seconds"
echo "========================================"
echo

stress --cpu "$CPU" --timeout "$TIME"

echo
echo "========================================"
echo "CPU Load Test Completed"
echo "========================================"
