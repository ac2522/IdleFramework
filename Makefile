.PHONY: dev server frontend build run install test lint format

install:
	pip install -e ".[dev,server]"
	cd frontend && npm install

server:
	uvicorn server.app:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run in two terminals:"
	@echo "  make server"
	@echo "  make frontend"

build:
	cd frontend && npm run build

run: build
	uvicorn server.app:app --port 8000

test:
	pytest tests/ -v

lint:
	ruff check src/ server/ tests/
	cd frontend && npx eslint .

format:
	ruff format src/ server/ tests/
