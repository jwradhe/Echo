#!/bin/bash

echo "Stopping containers..."
docker stop echo_web echo_db

echo "Removing containers..."
docker rm echo_web echo_db

echo "Done!"