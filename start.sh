#!/bin/bash

# Stoppa och rensa gamla containers
docker stop echo_web echo_db 2>/dev/null
docker rm echo_web echo_db 2>/dev/null

# Skapa nätverk om det inte finns
docker network create echo_network 2>/dev/null || true

# Skapa volym om den inte finns
docker volume create mysql_data 2>/dev/null || true

# Starta MySQL
echo "Starting MySQL..."
docker run -d \
  --name echo_db \
  --network echo_network \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=changemeCHANGEME123 \
  -e MYSQL_DATABASE=EchoDB \
  -e MYSQL_USER=echo \
  -e MYSQL_PASSWORD=changeme \
  -v mysql_data:/var/lib/mysql \
  -v "$(pwd)/schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro" \
  --restart unless-stopped \
  mysql:8.0

# Vänta på MySQL
echo "Waiting for MySQL to be ready..."
sleep 10

until docker exec echo_db mysqladmin ping -h localhost -u root -pchangemeCHANGEME123 --silent; do
  echo "Waiting for MySQL..."
  sleep 2
done

echo "MySQL is ready!"

# Bygg web-image
echo "Building web image..."
docker build -t echo_web:latest .

# Starta web
echo "Starting web application..."
docker run -d \
  --name echo_web \
  --network echo_network \
  -p 5001:5000 \
  --env-file .env \
  -e FLASK_APP=app.py \
  -e FLASK_ENV=development \
  -v "$(pwd)/app:/code/app" \
  --restart unless-stopped \
  echo_web:latest

echo "Done! Application running on http://localhost:5001"
docker ps