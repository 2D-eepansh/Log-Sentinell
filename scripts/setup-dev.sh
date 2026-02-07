#!/bin/bash
# Development Environment Setup Script for Linux/macOS
# Usage: bash scripts/setup-dev.sh
# Requires: Python 3.10+, pip, bash

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Arguments
GPU=false
SKIP_TEST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)
            GPU=true
            shift
            ;;
        --skip-test)
            SKIP_TEST=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Helper functions
step() {
    echo -e "${GREEN}▶ $1${NC}"
}

info() {
    echo -e "${BLUE}  ℹ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Banner
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Deriv Anomaly Copilot - Development Setup                 ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check Python installation
step "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 not found. Please install Python 3.10+ from https://www.python.org/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1)
success "$PYTHON_VERSION"

# Step 2: Verify Python version
step "Verifying Python version (requires 3.10+)..."
PYTHON_MINOR=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
MAJOR=$(echo $PYTHON_MINOR | cut -d. -f1)
MINOR=$(echo $PYTHON_MINOR | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    error "Python 3.10+ required. Found: $PYTHON_MINOR"
    exit 1
fi
success "Python $PYTHON_MINOR ✓"

# Step 3: Create virtual environment
step "Creating virtual environment..."
if [ -d "venv" ]; then
    info "Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        error "Failed to create virtual environment"
        exit 1
    fi
    success "Virtual environment created"
fi

# Step 4: Activate virtual environment
step "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    error "Failed to activate virtual environment"
    exit 1
fi
success "Virtual environment activated"

# Step 5: Upgrade pip
step "Upgrading pip..."
python -m pip install --upgrade pip --quiet
if [ $? -ne 0 ]; then
    error "Failed to upgrade pip"
    exit 1
fi
success "pip upgraded"

# Step 6: Install dependencies
step "Installing dependencies..."
DEPS=".[dev]"
if [ "$GPU" = true ]; then
    DEPS=".[dev,gpu]"
    info "GPU support enabled (bitsandbytes, flash-attn)"
fi

pip install -e "$DEPS"
if [ $? -ne 0 ]; then
    error "Failed to install dependencies"
    exit 1
fi
success "Dependencies installed"

# Step 7: Create .env file if it doesn't exist
step "Checking environment configuration..."
if [ ! -f ".env" ]; then
    info "Creating .env from .env.example..."
    cp .env.example .env
    success ".env created (review and customize as needed)"
else
    info ".env already exists"
fi

# Step 8: Create required directories
step "Creating required directories..."
for dir in data models logs; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        success "Created /$dir"
    else
        info "Directory /$dir already exists"
    fi
done

# Step 9: Run tests (optional)
if [ "$SKIP_TEST" = false ]; then
    step "Running test suite..."
    pytest -v
    if [ $? -ne 0 ]; then
        error "Some tests failed. Review output above."
        info "You can still use the environment. Fix issues and re-run: pytest"
    else
        success "All tests passed!"
    fi
else
    info "Test run skipped (use --skip-test to skip)"
fi

# Step 10: Verification
step "Verifying installation..."
python -c "
from src.core.config import config
print(f'✓ Config loaded: {config.app_name}')
print(f'✓ Environment: {config.environment}')
print(f'✓ Device: {config.device}')
"
if [ $? -ne 0 ]; then
    error "Verification failed"
    exit 1
fi

# Success banner
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Development Environment Ready!                         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

info "Next steps:"
info "1. Review and customize .env file"
info "2. Run: pytest (to run tests)"
info "3. Run: black src/ tests/ (to format code)"
info "4. Read: README.md for detailed documentation"
echo ""

info "Useful commands:"
info "  pytest                        # Run all tests"
info "  pytest -v                     # Verbose test output"
info "  pytest -m unit                # Run unit tests only"
info "  black src/ tests/             # Format code"
info "  isort src/ tests/             # Sort imports"
info "  ruff check src/ tests/        # Lint code"
info "  mypy src/                     # Type checking"
echo ""
