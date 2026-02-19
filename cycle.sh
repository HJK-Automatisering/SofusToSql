#!/bin/bash

INTERVAL=${RUN_INTERVAL_SECONDS:-3600}

echo "--- Starting Loop (Interval: $INTERVAL seconds) ---"

while true; do
    echo "[$(date)] Running Job..."
    
    python3 -u src/main.py
    
    echo "[$(date)] Job finished. Sleeping for $INTERVAL seconds..."
    sleep $INTERVAL
done