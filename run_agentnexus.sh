#!/bin/bash
echo "Starting AgentNexus Invoice Pro Commercial Server..."
python3 app.py &
sleep 2
if which xdg-open > /dev/null; then
    xdg-open http://localhost:8080/
elif which open > /dev/null; then
    open http://localhost:8080/
fi
