.PHONY: help install run test lint clean docker-build docker-run docker-stop

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt
	pip install pytest ruff

run: ## Run the dashboard locally (simulator mode)
	python run.py

run-ros2: ## Run with ROS 2 source (must be sourced first)
	TELEMETRY_SOURCE=ros2 python run.py

test: ## Run pytest suite
	pytest tests/ -v

lint: ## Lint with ruff
	ruff check app/ tests/

clean: ## Remove caches and build artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info

docker-build: ## Build the Docker image
	docker build -t yana-robots:latest .

docker-run: ## Start the container with docker-compose
	docker compose up -d

docker-stop: ## Stop the container
	docker compose down

docker-logs: ## Tail container logs
	docker compose logs -f
