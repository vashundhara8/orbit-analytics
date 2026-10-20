# =============================================================================
# Toolchain resolution
#
# This project strictly targets Python 3.13 via the `saas_env` pyenv virtualenv.
# We resolve every tool through the env prefix so things work whether or not
# pyenv-virtualenv auto-activation is configured in your shell.
#
# If `saas_env` doesn't exist yet, run:
#   pyenv install -s 3.13.3
#   pyenv virtualenv 3.13.3 saas_env
#   pyenv local saas_env
# =============================================================================

PYENV_VENV       := saas_env
SAAS_ENV_PREFIX  := $(shell pyenv prefix $(PYENV_VENV) 2>/dev/null)

PYTHON           := $(SAAS_ENV_PREFIX)/bin/python
PIP              := $(PYTHON) -m pip
RUFF             := $(SAAS_ENV_PREFIX)/bin/ruff
PYTEST           := $(SAAS_ENV_PREFIX)/bin/pytest
STREAMLIT        := $(SAAS_ENV_PREFIX)/bin/streamlit
SPHINX_BUILD     := $(SAAS_ENV_PREFIX)/bin/sphinx-build
SPHINX_AUTOBUILD := $(SAAS_ENV_PREFIX)/bin/sphinx-autobuild

.PHONY: help _check-env install all-env generate transform analyze pipeline \
        app docs docs-build docs-clean test lint fmt clean

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v '^_' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# -----------------------------------------------------------------------------
# Environment guardrail
# -----------------------------------------------------------------------------

_check-env:
	@command -v pyenv >/dev/null 2>&1 || { \
		echo "ERROR: pyenv is not installed."; \
		echo "       Install it first: https://github.com/pyenv/pyenv#installation"; \
		exit 1; \
	}
	@test -n "$(SAAS_ENV_PREFIX)" || { \
		echo "ERROR: pyenv virtualenv '$(PYENV_VENV)' not found."; \
		echo "       Run:"; \
		echo "         pyenv install -s 3.13.3"; \
		echo "         pyenv virtualenv 3.13.3 $(PYENV_VENV)"; \
		echo "         pyenv local $(PYENV_VENV)"; \
		exit 1; \
	}
	@$(PYTHON) -c "import sys; ok = sys.version_info[:2] == (3, 13); print(sys.version.split()[0]); sys.exit(0 if ok else 1)" >/tmp/.saas-pyver 2>/dev/null || { \
		echo "ERROR: $(PYENV_VENV) must be Python 3.13.x. Got: $$(cat /tmp/.saas-pyver 2>/dev/null || echo unknown)"; \
		echo "       Recreate the env:"; \
		echo "         pyenv uninstall -f $(PYENV_VENV)"; \
		echo "         pyenv install -s 3.13.3"; \
		echo "         pyenv virtualenv 3.13.3 $(PYENV_VENV)"; \
		echo "         pyenv local $(PYENV_VENV)"; \
		exit 1; \
	}
	@rm -f /tmp/.saas-pyver

# -----------------------------------------------------------------------------
# Bootstrap
# -----------------------------------------------------------------------------

install: _check-env ## Install core + dev dependencies into saas_env
	$(PIP) install -e ".[dev]"

all-env: _check-env ## Install ALL extras (dev + streamlit + docs) -- one-shot bootstrap
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,streamlit,docs]"
	@echo
	@echo "Environment ready. Next steps:"
	@echo "  make pipeline   # generate data, build SQL marts, run analysis"
	@echo "  make app        # start the Streamlit dashboard"
	@echo "  make docs       # browse the project documentation"

# -----------------------------------------------------------------------------
# Data pipeline
# -----------------------------------------------------------------------------

generate: _check-env ## Generate synthetic SaaS data into data/raw/
	$(PYTHON) -m python.src.generate_data

transform: _check-env ## Run DuckDB SQL staging + marts, output to data/processed/
	$(PYTHON) -m python.src.run_sql_models

analyze: _check-env ## Run Python analysis (funnel, cohort, A/B test, churn scoring)
	$(PYTHON) -m python.src.analysis

pipeline: generate transform analyze ## Full pipeline: generate + transform + analyze

# -----------------------------------------------------------------------------
# Streamlit dashboard
# -----------------------------------------------------------------------------

app: _check-env ## Start the Streamlit dashboard on port 8501
	$(STREAMLIT) run streamlit_app/app.py --server.port 8501

# -----------------------------------------------------------------------------
# Documentation (Sphinx)
# -----------------------------------------------------------------------------

docs: _check-env ## Build and serve docs with live reload (port 8000)
	$(SPHINX_AUTOBUILD) docs docs/_build/html --port 8000 --open-browser

docs-build: _check-env ## One-shot build of docs to docs/_build/html
	$(SPHINX_BUILD) -b html docs docs/_build/html

docs-clean: ## Remove generated documentation artifacts
	rm -rf docs/_build

# -----------------------------------------------------------------------------
# Quality
# -----------------------------------------------------------------------------

test: _check-env ## Run pytest
	$(PYTEST)

lint: _check-env ## Lint with ruff
	$(RUFF) check .

fmt: _check-env ## Format with ruff
	$(RUFF) format .

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

clean: ## Remove generated data files
	rm -rf data/raw/*.parquet data/processed/*.parquet
