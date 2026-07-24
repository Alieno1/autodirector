.PHONY: install install-dev run-demo test lint format clean help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime dependencies
	pip install -r requirements.txt

install-dev:  ## Install all dependencies including dev/test
	pip install -r requirements-dev.txt

run-demo:  ## Run pipeline in DEMO mode (no API keys needed)
	python3 main.py sample_input/story.txt

run-demo-verbose:  ## Run pipeline in DEMO mode with verbose logging
	python3 main.py sample_input/story.txt --verbose

test:  ## Run the full test suite
	pytest tests/ -v --tb=short

test-cov:  ## Run tests with coverage report
	pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

clean:  ## Remove generated temp files and output videos
	rm -rf temp/*
	rm -f output/*.mp4
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
