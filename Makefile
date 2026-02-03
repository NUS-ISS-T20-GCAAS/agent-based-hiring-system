.PHONY: build-all build-frontend build-coordinator build-resume up down

# Build all services individually
build-all: build-frontend build-coordinator build-resume

build-frontend:
	cd frontend && docker build -t frontend .

build-coordinator:
	cd services/coordinator-agent && docker build -t coordinator-agent .

build-resume:
	cd services/resume-intake-agent && docker build -t resume-intake-agent .

# Using docker-compose
compose-build-all:
	docker-compose -f infra/docker-compose.yml build

compose-build-frontend:
	docker-compose -f infra/docker-compose.yml build frontend

compose-build-coordinator:
	docker-compose -f infra/docker-compose.yml build coordinator-agent

compose-build-resume:
	docker-compose -f infra/docker-compose.yml build resume-intake-agent

# Run services
up:
	docker-compose -f infra/docker-compose.yml up

down:
	docker-compose -f infra/docker-compose.yml down