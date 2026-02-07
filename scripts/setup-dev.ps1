# Development Environment Setup Script for Windows
# Usage: .\scripts\setup-dev.ps1
# Requires: PowerShell 5.1+, Python 3.10+, pip

param(
    [switch]$GPU = $false,
    [switch]$SkipTest = $false
)

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Deriv Anomaly Copilot - Development Setup                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Color functions
function Write-Step { param([string]$msg); Write-Host "▶ $msg" -ForegroundColor Green }
function Write-Info { param([string]$msg); Write-Host "  ℹ $msg" -ForegroundColor Blue }
function Write-Error-Custom { param([string]$msg); Write-Host "✗ $msg" -ForegroundColor Red }
function Write-Success { param([string]$msg); Write-Host "✓ $msg" -ForegroundColor Green }

# Step 1: Check Python installation
Write-Step "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success $pythonVersion
} catch {
    Write-Error-Custom "Python not found. Please install Python 3.10+ from https://www.python.org/"
    exit 1
}

# Step 2: Check Python version
Write-Step "Verifying Python version (requires 3.10+)..."
$version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major, $minor = $version.Split('.')
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 10)) {
    Write-Error-Custom "Python 3.10+ required. Found: $version"
    exit 1
}
Write-Success "Python $version ✓"

# Step 3: Create virtual environment
Write-Step "Creating virtual environment..."
if (Test-Path "venv") {
    Write-Info "Virtual environment already exists. Skipping creation."
} else {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to create virtual environment"
        exit 1
    }
    Write-Success "Virtual environment created"
}

# Step 4: Activate virtual environment
Write-Step "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to activate virtual environment"
    exit 1
}
Write-Success "Virtual environment activated"

# Step 5: Upgrade pip
Write-Step "Upgrading pip..."
python -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to upgrade pip"
    exit 1
}
Write-Success "pip upgraded"

# Step 6: Install dependencies
Write-Step "Installing dependencies..."
$deps = ".[dev]"
if ($GPU) {
    $deps = ".[dev,gpu]"
    Write-Info "GPU support enabled (bitsandbytes, flash-attn)"
}

pip install -e $deps
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to install dependencies"
    exit 1
}
Write-Success "Dependencies installed"

# Step 7: Create .env file if it doesn't exist
Write-Step "Checking environment configuration..."
if (-not (Test-Path ".env")) {
    Write-Info "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Success ".env created (review and customize as needed)"
} else {
    Write-Info ".env already exists"
}

# Step 8: Create required directories
Write-Step "Creating required directories..."
@("data", "models", "logs") | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ | Out-Null
        Write-Success "Created /$_"
    } else {
        Write-Info "Directory /$_ already exists"
    }
}

# Step 9: Run tests (optional)
if (-not $SkipTest) {
    Write-Step "Running test suite..."
    pytest -v
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Some tests failed. Review output above."
        Write-Info "You can still use the environment. Fix issues and re-run: pytest"
    } else {
        Write-Success "All tests passed!"
    }
} else {
    Write-Info "Test run skipped (use -SkipTest:$false to run)"
}

# Step 10: Verification
Write-Step "Verifying installation..."
python -c "
from src.core.config import config
print(f'✓ Config loaded: {config.app_name}')
print(f'✓ Environment: {config.environment}')
print(f'✓ Device: {config.device}')
"
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Verification failed"
    exit 1
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✓ Development Environment Ready!                         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Info "Next steps:"
Write-Info "1. Review and customize .env file"
Write-Info "2. Run: pytest (to run tests)"
Write-Info "3. Run: black src/ tests/ (to format code)"
Write-Info "4. Read: README.md for detailed documentation"
Write-Host ""

Write-Info "Useful commands:"
Write-Info "  pytest                        # Run all tests"
Write-Info "  pytest -v                     # Verbose test output"
Write-Info "  pytest -m unit                # Run unit tests only"
Write-Info "  black src/ tests/             # Format code"
Write-Info "  isort src/ tests/             # Sort imports"
Write-Info "  ruff check src/ tests/        # Lint code"
Write-Info "  mypy src/                     # Type checking"
Write-Host ""
