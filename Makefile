.PHONY: build-all build-frontend build-coordinator build-resume build-screening up down migrate-db migrate-db-services

# Build all services individually
build-all: build-frontend build-coordinator build-resume build-screening

build-frontend:
	cd frontend && docker build -t frontend .

build-coordinator:
	cd services/coordinator-agent && docker build -t coordinator-agent .

build-resume:
	cd services/resume-intake-agent && docker build -t resume-intake-agent .

build-screening:
	cd services/screening-agent && docker build -t screening-agent .

# Using docker-compose
compose-build-all:
	docker-compose -f infra/docker-compose.yml build

compose-build-frontend:
	docker-compose -f infra/docker-compose.yml build frontend

compose-build-coordinator:
	docker-compose -f infra/docker-compose.yml build coordinator-agent

compose-build-resume:
	docker-compose -f infra/docker-compose.yml build resume-intake-agent

compose-build-screening:
	docker-compose -f infra/docker-compose.yml build screening-agent

# Run services
up:
	docker-compose -f infra/docker-compose.yml up

down:
	docker-compose -f infra/docker-compose.yml down

migrate-db:
	sh db/migrate.sh infra/docker-compose.yml

migrate-db-services:
	sh db/migrate.sh services/docker-compose.yml
