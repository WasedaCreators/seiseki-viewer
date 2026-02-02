.PHONY: install system-deps setup-db backend-deps frontend-deps build-frontend run run-backend run-frontend clean stop help

# =============================================================================
# Main Targets
# =============================================================================

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup targets:"
	@echo "  install       - Install all dependencies (run this first on fresh Ubuntu 22.04)"
	@echo "  system-deps   - Install system packages (Python, Node.js, Chrome, MySQL)"
	@echo "  backend-deps  - Install Python dependencies in virtual environment"
	@echo "  frontend-deps - Install Node.js dependencies"
	@echo "  setup-db      - Setup MySQL database"
	@echo "  build-frontend- Build frontend for production"
	@echo ""
	@echo "Run targets:"
	@echo "  run           - Start both backend and frontend"
	@echo "  run-backend   - Start backend only"
	@echo "  run-frontend  - Start frontend only"
	@echo ""
	@echo "Database targets:"
	@echo "  migrate-db    - Add lab preference columns to existing database"
	@echo "  show-schema   - Show current gpadata table schema"
	@echo "  show-database - Show database contents (GPA & lab preferences)"
	@echo "  hash          - Migrate student IDs to SHA-256 hashes"
	@echo ""
	@echo "Other targets:"
	@echo "  stop          - Stop all running processes"
	@echo "  clean         - Remove build artifacts and dependencies"

install: system-deps backend-deps frontend-deps setup-db build-frontend
	@echo ""
	@echo "=============================================="
	@echo "Installation complete!"
	@echo "Run 'make run' to start the application."
	@echo "Frontend: http://localhost:3001"
	@echo "Backend:  http://localhost:8001"
	@echo "=============================================="

# =============================================================================
# System Dependencies
# =============================================================================

system-deps:
	@echo "=============================================="
	@echo "Installing System Dependencies..."
	@echo "=============================================="
	sudo apt-get update
	@# Python
	sudo apt-get install -y python3 python3-pip python3-venv
	@# Build tools and utilities
	sudo apt-get install -y curl unzip wget gnupg ca-certificates
	@# MySQL
	sudo apt-get install -y mysql-server
	@# Install Google Chrome (stable) for better Selenium compatibility
	@if ! command -v google-chrome >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then \
		echo "Installing Google Chrome..."; \
		wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
		sudo dpkg -i /tmp/google-chrome.deb || sudo apt-get install -f -y && \
		rm -f /tmp/google-chrome.deb; \
	else \
		echo "Chrome/Chromium is already installed."; \
	fi
	@# Fallback: Install chromium if Google Chrome failed
	@if ! command -v google-chrome >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then \
		echo "Installing Chromium as fallback..."; \
		sudo apt-get install -y chromium-browser || sudo apt-get install -y chromium; \
	fi
	@# Install Node.js 20.x LTS
	@if ! command -v node >/dev/null 2>&1; then \
		echo "Installing Node.js 20.x LTS..."; \
		curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && \
		sudo apt-get install -y nodejs; \
	else \
		NODE_VERSION=$$(node --version); \
		echo "Node.js $$NODE_VERSION is already installed."; \
	fi
	@echo "System dependencies installed."

# =============================================================================
# Database Setup
# =============================================================================

setup-db:
	@echo "=============================================="
	@echo "Setting up MySQL Database..."
	@echo "=============================================="
	@# Start MySQL service
	sudo service mysql start || sudo systemctl start mysql || echo "Warning: Could not start MySQL service"
	@# Wait for MySQL to be ready
	@sleep 3
	@# Create Database and User (using sudo mysql which uses auth_socket)
	-sudo mysql -e "CREATE DATABASE IF NOT EXISTS seiseki CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
	-sudo mysql -e "CREATE USER IF NOT EXISTS 'seiseki'@'localhost' IDENTIFIED BY 'seiseki-mitai';"
	-sudo mysql -e "CREATE USER IF NOT EXISTS 'seiseki'@'127.0.0.1' IDENTIFIED BY 'seiseki-mitai';"
	-sudo mysql -e "ALTER USER 'seiseki'@'localhost' IDENTIFIED BY 'seiseki-mitai';"
	-sudo mysql -e "ALTER USER 'seiseki'@'127.0.0.1' IDENTIFIED BY 'seiseki-mitai';"
	-sudo mysql -e "GRANT ALL PRIVILEGES ON seiseki.* TO 'seiseki'@'localhost';"
	-sudo mysql -e "GRANT ALL PRIVILEGES ON seiseki.* TO 'seiseki'@'127.0.0.1';"
	-sudo mysql -e "FLUSH PRIVILEGES;"
	@echo "MySQL Database configured."
	@echo "  Database: seiseki"
	@echo "  User: seiseki"
	@echo "  Password: seiseki-mitai"

# =============================================================================
# Backend Dependencies
# =============================================================================

backend-deps:
	@echo "=============================================="
	@echo "Setting up Backend (Python)..."
	@echo "=============================================="
	@# Create virtual environment
	cd waseda-grade-api && python3 -m venv .venv
	@# Upgrade pip
	cd waseda-grade-api && .venv/bin/pip install --upgrade pip
	@# Install dependencies
	cd waseda-grade-api && .venv/bin/pip install -r requirements.txt
	@echo "Backend dependencies installed."

# =============================================================================
# Frontend Dependencies
# =============================================================================

frontend-deps:
	@echo "=============================================="
	@echo "Setting up Frontend (Node.js)..."
	@echo "=============================================="
	cd frontend && npm install
	@echo "Frontend dependencies installed."

build-frontend:
	@echo "=============================================="
	@echo "Building Frontend for Production..."
	@echo "=============================================="
	cd frontend && npm run build
	@echo "Frontend build complete."

# =============================================================================
# Run Targets
# =============================================================================

run:
	@echo "=============================================="
	@echo "Starting Application..."
	@echo "=============================================="
	@# Ensure MySQL is running
	@sudo service mysql start || sudo systemctl start mysql || true
	@free -h 2>/dev/null || true
	@echo ""
	python3 run.py

run-backend:
	@echo "Starting Backend only..."
	@sudo service mysql start || sudo systemctl start mysql || true
	cd waseda-grade-api && .venv/bin/python main.py

run-frontend:
	@echo "Starting Frontend only..."
	cd frontend && BACKEND_URL=http://127.0.0.1:8001 npm start

# =============================================================================
# Utility Targets
# =============================================================================

stop:
	@echo "Stopping all processes..."
	@-pkill -f "python.*main.py" 2>/dev/null || true
	@-pkill -f "node.*next" 2>/dev/null || true
	@-pkill -f "chrome" 2>/dev/null || true
	@-pkill -f "chromedriver" 2>/dev/null || true
	@echo "Processes stopped."

clean:
	@echo "Cleaning up..."
	rm -rf waseda-grade-api/.venv
	rm -rf frontend/node_modules
	rm -rf frontend/.next
	@echo "Clean complete."

hash:
	@echo "Migrating student IDs to SHA-256 hashes..."
	cd waseda-grade-api && .venv/bin/python migrate_hashes.py

migrate-db:
	@echo "=============================================="
	@echo "Migrating Database Schema..."
	@echo "=============================================="
	@sudo service mysql start || sudo systemctl start mysql || true
	@# Add lab preference columns if they don't exist
	-mysql -u seiseki -pseiseki-mitai seiseki -e "ALTER TABLE gpadata ADD COLUMN lab_choice_1 VARCHAR(50);" 2>/dev/null || echo "lab_choice_1 column already exists"
	-mysql -u seiseki -pseiseki-mitai seiseki -e "ALTER TABLE gpadata ADD COLUMN lab_choice_2 VARCHAR(50);" 2>/dev/null || echo "lab_choice_2 column already exists"
	-mysql -u seiseki -pseiseki-mitai seiseki -e "ALTER TABLE gpadata ADD COLUMN lab_choice_3 VARCHAR(50);" 2>/dev/null || echo "lab_choice_3 column already exists"
	-mysql -u seiseki -pseiseki-mitai seiseki -e "ALTER TABLE gpadata ADD COLUMN lab_choice_4 VARCHAR(50);" 2>/dev/null || echo "lab_choice_4 column already exists"
	-mysql -u seiseki -pseiseki-mitai seiseki -e "ALTER TABLE gpadata ADD COLUMN lab_choice_5 VARCHAR(50);" 2>/dev/null || echo "lab_choice_5 column already exists"
	-mysql -u seiseki -pseiseki-mitai seiseki -e "ALTER TABLE gpadata ADD COLUMN lab_choice_6 VARCHAR(50);" 2>/dev/null || echo "lab_choice_6 column already exists"
	-mysql -u seiseki -pseiseki-mitai seiseki -e "ALTER TABLE gpadata ADD COLUMN uses_recommendation BOOLEAN;" 2>/dev/null || echo "uses_recommendation column already exists"
	-mysql -u seiseki -pseiseki-mitai seiseki -e "ALTER TABLE gpadata ADD COLUMN lab_updated_at DATETIME;" 2>/dev/null || echo "lab_updated_at column already exists"
	@echo "Database migration complete."

show-schema:
	@echo "=============================================="
	@echo "Current Database Schema (gpadata table):"
	@echo "=============================================="
	@sudo service mysql start || sudo systemctl start mysql || true
	mysql -u seiseki -pseiseki-mitai seiseki -e "DESCRIBE gpadata;"

show-database:
	@echo "=============================================="
	@echo "Database Contents (gpadata table)"
	@echo "=============================================="
	@sudo service mysql start || sudo systemctl start mysql || true
	@echo ""
	@echo "--- Summary ---"
	@mysql -u seiseki -pseiseki-mitai seiseki -e "SELECT COUNT(*) AS '総レコード数', COUNT(avg_gpa) AS 'GPA登録数', COUNT(lab_choice_1) AS '研究室志望登録数' FROM gpadata;" 2>/dev/null || echo "No data or table not found"
	@echo ""
	@echo "--- GPA Data (student_id is hashed) ---"
	@mysql -u seiseki -pseiseki-mitai seiseki -e "SELECT CONCAT(LEFT(student_id, 8), '...') AS student_id_short, ROUND(avg_gpa, 2) AS avg_gpa, timestamp FROM gpadata WHERE avg_gpa IS NOT NULL ORDER BY timestamp DESC LIMIT 20;" 2>/dev/null || echo "No GPA data"
	@echo ""
	@echo "--- Lab Preferences ---"
	@mysql -u seiseki -pseiseki-mitai seiseki -e "SELECT CONCAT(LEFT(student_id, 8), '...') AS student_id_short, lab_choice_1 AS '第1希望', lab_choice_2 AS '第2希望', lab_choice_3 AS '第3希望', CASE WHEN uses_recommendation THEN '○' ELSE '×' END AS '自己推薦', lab_updated_at FROM gpadata WHERE lab_choice_1 IS NOT NULL ORDER BY lab_updated_at DESC LIMIT 20;" 2>/dev/null || echo "No lab preference data"
	@echo ""
	@echo "(Showing latest 20 records each)"

# =============================================================================
# Development Targets
# =============================================================================

dev-frontend:
	@echo "Starting Frontend in development mode..."
	cd frontend && BACKEND_URL=http://127.0.0.1:8001 npm run dev

lint:
	@echo "Running linter..."
	cd frontend && npm run lint
