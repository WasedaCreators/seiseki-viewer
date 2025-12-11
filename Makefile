.PHONY: install system-deps setup-db backend-deps frontend-deps build-frontend run clean

install: system-deps setup-db backend-deps frontend-deps build-frontend

system-deps:
	@echo "Installing System Dependencies (requires sudo)..."
	sudo apt-get update
	sudo apt-get install -y python3 python3-pip python3-venv curl unzip mysql-server
	@# Install Chromium and Driver (Try chromium-browser/chromedriver first, then chromium/chromium-driver)
	sudo apt-get install -y chromium-browser chromium-chromedriver || sudo apt-get install -y chromium chromium-driver
	@# Install Node.js 18.x if not present
	@if ! command -v node >/dev/null 2>&1; then \
		echo "Installing Node.js 18.x..."; \
		curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -; \
		sudo apt-get install -y nodejs; \
	else \
		echo "Node.js is already installed."; \
	fi

setup-db:
	@echo "Setting up Local MySQL Database..."
	@# Ensure MySQL is running
	sudo service mysql start || sudo systemctl start mysql || echo "Could not start MySQL service, please start it manually."
	@# Create Database and User
	@echo "Configuring MySQL users and database..."
	sudo mysql -e "CREATE DATABASE IF NOT EXISTS seiseki;"
	sudo mysql -e "CREATE USER IF NOT EXISTS 'seiseki'@'localhost' IDENTIFIED BY 'seiseki-mitai';" || true
	sudo mysql -e "CREATE USER IF NOT EXISTS 'seiseki'@'127.0.0.1' IDENTIFIED BY 'seiseki-mitai';" || true
	sudo mysql -e "GRANT ALL PRIVILEGES ON seiseki.* TO 'seiseki'@'localhost';"
	sudo mysql -e "GRANT ALL PRIVILEGES ON seiseki.* TO 'seiseki'@'127.0.0.1';"
	sudo mysql -e "FLUSH PRIVILEGES;"
	@echo "MySQL Database configured."

backend-deps:
	@echo "Setting up Python Virtual Environment..."
	cd waseda-grade-api && python3 -m venv .venv
	@echo "Installing Backend Dependencies..."
	cd waseda-grade-api && .venv/bin/pip install -r requirements.txt

frontend-deps:
	@echo "Installing Frontend Dependencies..."
	cd frontend && npm install

build-frontend:
	@echo "Building Frontend for Production..."
	cd frontend && npm run build

run:
	@echo "Checking memory status..."
	@free -h || true
	@echo "Starting Process Manager..."
	python3 run.py

hash:
	@echo "Migrating student IDs to SHA-256 hashes..."
	cd waseda-grade-api && .venv/bin/python migrate_hashes.py
	@echo "Starting servers using Python script..."
	@python3 run.py
