.PHONY: help install build-orchestrator build-publisher build-lambdas \
        terraform-init terraform-plan terraform-apply terraform-destroy \
        run-controller lint typecheck test coverage clean

help:
	@echo "AI Content Automation Platform"
	@echo ""
	@echo "Usage:"
	@echo "  make install            Install all dependencies"
	@echo "  make build-lambdas      Build Lambda deployment packages"
	@echo "  make run-controller     Start the MacBook Controller"
	@echo "  make terraform-plan     Preview infrastructure changes"
	@echo "  make terraform-apply    Deploy infrastructure"
	@echo "  make lint               Run ruff linter"
	@echo "  make typecheck          Run mypy type checker"
	@echo "  make test               Run tests"
	@echo "  make coverage           Run tests with coverage report"
	@echo "  make clean              Clean build artifacts"

install:
	poetry install --extras "orchestrator publisher macbook kali"
	poetry install --extras dev

LAMBDA_IMAGE ?= public.ecr.aws/lambda/python:3.13

build-orchestrator:
	rm -rf build/orchestrator-package build/orchestrator.zip
	mkdir -p build
	poetry export --extras orchestrator -f requirements.txt --output build/orchestrator-requirements.txt
	docker run --rm --entrypoint pip --platform linux/arm64 \
		-v "$(PWD)/build":/build \
		-w /build $(LAMBDA_IMAGE) \
		install -r /build/orchestrator-requirements.txt -t /build/orchestrator-package/
	cp -r aws build/orchestrator-package/
	cd build/orchestrator-package && zip -r ../orchestrator.zip .

build-publisher:
	rm -rf build/publisher-package build/publisher.zip
	mkdir -p build
	poetry export --extras publisher -f requirements.txt --output build/publisher-requirements.txt
	docker run --rm --entrypoint pip --platform linux/arm64 \
		-v "$(PWD)/build":/build \
		-w /build $(LAMBDA_IMAGE) \
		install -r /build/publisher-requirements.txt -t /build/publisher-package/
	cp -r aws build/publisher-package/
	cd build/publisher-package && zip -r ../publisher.zip .

build-lambdas: build-orchestrator build-publisher

run-controller:
	python -m macbook.controller.main

terraform-init:
	cd infrastructure/terraform && terraform init

terraform-plan:
	cd infrastructure/terraform && terraform plan

terraform-apply:
	cd infrastructure/terraform && terraform apply

terraform-destroy:
	cd infrastructure/terraform && terraform destroy

lint:
	ruff check .

typecheck:
	mypy aws/ macbook/ kali/

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=aws --cov=macbook --cov=kali --cov-report=term-missing --cov-fail-under=90

clean:
	rm -rf build/ artifacts/ logs/ .pytest_cache/ .ruff_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.py[cod]' -delete
