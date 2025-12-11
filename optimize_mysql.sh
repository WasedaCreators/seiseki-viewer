#!/bin/bash
set -e

echo "Configuring MySQL for low memory usage..."

CONFIG_FILE="/etc/mysql/mysql.conf.d/mysqld.cnf"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config file $CONFIG_FILE not found. Trying /etc/mysql/my.cnf"
    CONFIG_FILE="/etc/mysql/my.cnf"
fi

# Backup existing config
sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"

# Append low memory settings if not present
if ! grep -q "performance_schema" "$CONFIG_FILE"; then
    echo "Adding low memory settings to $CONFIG_FILE"
    cat <<EOF | sudo tee -a "$CONFIG_FILE"

[mysqld]
performance_schema = OFF
innodb_buffer_pool_size = 128M
innodb_log_buffer_size = 8M
key_buffer_size = 16M
max_connections = 20
table_open_cache = 64
thread_cache_size = 4
host_cache_size = 0
EOF
else
    echo "Settings might already exist. Please check $CONFIG_FILE manually."
fi

echo "Restarting MySQL..."
sudo service mysql restart

echo "MySQL optimized."
