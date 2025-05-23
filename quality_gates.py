#!/usr/bin/env python3
"""
Retroclamp Quality Gates Setup
Combines the best of both approaches: clean structure + comprehensive features

Usage:
    python quality_gates.py --install
    python quality_gates.py --install --full  # Include all advanced features
"""

import argparse
import io
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


# Ensure UTF-8 output for emojis on Windows consoles
def _configure_utf8_stdout():
    if hasattr(sys.stdout, "reconfigure"):  # Python 3.7+
        sys.stdout.reconfigure(encoding="utf-8")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


_configure_utf8_stdout()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_basic_config() -> Dict[str, Any]:
    """Basic quality gates configuration for minimal setup."""
    return {
        "pre_commit": {
            "repos": [
                {
                    "repo": "https://github.com/psf/black",
                    "rev": "23.12.1",
                    "hooks": [{"id": "black", "args": ["--line-length=88"]}],
                },
                {
                    "repo": "https://github.com/PyCQA/isort",
                    "rev": "5.13.2",
                    "hooks": [{"id": "isort", "args": ["--profile=black"]}],
                },
                {
                    "repo": "https://github.com/PyCQA/flake8",
                    "rev": "6.1.0",
                    "hooks": [
                        {
                            "id": "flake8",
                            "args": [
                                "--max-line-length=88",
                                "--extend-ignore=E203,W503",
                            ],
                        }
                    ],
                },
                {
                    "repo": "https://github.com/pre-commit/pre-commit-hooks",
                    "rev": "v4.5.0",
                    "hooks": [
                        {"id": "check-yaml"},
                        {"id": "end-of-file-fixer"},
                        {"id": "trailing-whitespace"},
                        {"id": "check-merge-conflict"},
                    ],
                },
            ]
        },
        "quality_thresholds": {
            "max_complexity": 10,
            "min_coverage": 70,
            "min_docstring_coverage": 50,
        },
    }


def load_full_config() -> Dict[str, Any]:
    """Comprehensive configuration with advanced features."""
    basic = load_basic_config()

    # Add advanced pre-commit hooks
    basic["pre_commit"]["repos"].extend(
        [
            {
                "repo": "https://github.com/PyCQA/bandit",
                "rev": "1.7.5",
                "hooks": [{"id": "bandit", "args": ["-r", ".", "-ll"]}],
            },
            {
                "repo": "https://github.com/pre-commit/mirrors-mypy",
                "rev": "v1.8.0",
                "hooks": [{"id": "mypy", "args": ["--ignore-missing-imports"]}],
            },
            {
                "repo": "local",
                "hooks": [
                    {
                        "id": "retroclamp-chdman-security",
                        "name": "CHDMAN Security Check",
                        "entry": "python scripts/chdman_security_check.py",
                        "language": "system",
                        "files": r"^core/.*\.py$",
                    },
                    {
                        "id": "retroclamp-plugin-validation",
                        "name": "Plugin API Validation",
                        "entry": "python scripts/validate_plugins.py",
                        "language": "system",
                        "files": r"^tools/.*\.py$",
                    },
                ],
            },
        ]
    )

    # Add advanced thresholds
    basic["quality_thresholds"].update(
        {"max_function_length": 50, "max_class_length": 200, "min_comment_ratio": 15.0}
    )

    return basic


def create_pre_commit_config(project_root: Path, config: Dict[str, Any]) -> None:
    """Generate .pre-commit-config.yaml."""
    cfg_path = project_root / ".pre-commit-config.yaml"

    try:
        import yaml
    except ImportError:
        logger.error("PyYAML is required. Install with: pip install pyyaml")
        sys.exit(1)

    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config["pre_commit"], f, sort_keys=False, default_flow_style=False
            )
        print("✅ Created pre-commit configuration:", cfg_path)
    except Exception as e:
        print(f"❌ Failed to create pre-commit config: {e}")
        sys.exit(1)


def install_pre_commit_hooks(project_root: Path) -> bool:
    """Install pre-commit git hooks. Returns True if successful."""
    try:
        # Check if pre-commit is available
        subprocess.run(
            ["pre-commit", "--version"], capture_output=True, check=True, timeout=10
        )

        # Install hooks
        subprocess.run(
            ["pre-commit", "install"], cwd=str(project_root), check=True, timeout=30
        )
        print("✅ Installed pre-commit hooks")
        return True

    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to install pre-commit hooks: {e}")
        print("💡 You can install them later with: pre-commit install")
        return False
    except FileNotFoundError:
        print("⚠️  pre-commit not found. Install with: pip install pre-commit")
        print("💡 Then run: pre-commit install")
        return False


def create_github_actions_workflow(
    project_root: Path, full_setup: bool = False
) -> None:
    """Create GitHub Actions workflow for quality gates."""
    workflows_dir = project_root / ".github" / "workflows"

    try:
        workflows_dir.mkdir(parents=True, exist_ok=True)
        wf_path = workflows_dir / "quality_gates.yml"

        # Basic workflow
        workflow_content = """name: Quality Gates

on:
  push:
    branches: [ main, dev-* ]
  pull_request:
    branches: [ main ]

jobs:
  quality-checks:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', '3.11']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pre-commit pytest pytest-cov bandit safety

    - name: Run pre-commit hooks
      run: pre-commit run --all-files

    - name: Run tests with coverage
      run: |
        if [ -d "tests" ] || find . -name "*test*.py" | grep -q .; then
          pytest --cov=. --cov-report=xml --cov-report=term
        else
          echo "No tests found - please add unit tests"
        fi

    - name: Security checks
      run: |
        bandit -r . -f json -o bandit-report.json || true
        safety check --json --output safety-report.json || true

    - name: Upload coverage to Codecov
      if: matrix.python-version == '3.10'
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
"""

        # Add Retroclamp-specific checks for full setup
        if full_setup:
            workflow_content += """
    - name: Retroclamp-specific checks
      run: |
        # Run custom analysis if available
        if [ -f "retroclamp_analyzer.py" ]; then
          python retroclamp_analyzer.py . --output analysis-report.json
        fi

        # Run focused component analysis if available
        if [ -f "focused_analysis.py" ]; then
          python focused_analysis.py all . --output focused-report.json
        fi

    - name: Archive analysis reports
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: analysis-reports-${{ matrix.python-version }}
        path: |
          bandit-report.json
          safety-report.json
          analysis-report.json
          focused-report.json
"""

        with open(wf_path, "w", encoding="utf-8") as f:
            f.write(workflow_content)
        print("✅ Created GitHub Actions workflow:", wf_path)

    except Exception as e:
        print(f"❌ Failed to create GitHub Actions workflow: {e}")
        sys.exit(1)


def create_pyproject_toml(project_root: Path) -> None:
    """Create pyproject.toml with tool configurations."""
    toml_path = project_root / "pyproject.toml"

    toml_content = """[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "retroclamp"
description = "Modern GUI for CHDMAN operations and disk image management"
readme = "README.md"
license = {text = "MIT"}
dynamic = ["version", "dependencies"]

[tool.black]
line-length = 88
target-version = ['py38', 'py39', 'py310', 'py311']

[tool.isort]
profile = "black"
line_length = 88

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]

[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --cov=. --cov-report=term-missing"
testpaths = ["tests"]

[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv"]
skips = ["B101"]

[tool.mypy]
python_version = "3.8"
ignore_missing_imports = true
warn_return_any = true
warn_unused_configs = true
"""

    try:
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(toml_content)
        print("✅ Created pyproject.toml:", toml_path)
    except Exception as e:
        print(f"❌ Failed to create pyproject.toml: {e}")
        sys.exit(1)


def create_makefile(project_root: Path) -> None:
    """Create Makefile for common development tasks."""
    makefile_path = project_root / "Makefile"

    makefile_content = """# Retroclamp Development Makefile

.PHONY: help install dev-install test lint format clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; \
    {printf "  \\033[36m%-15s\\033[0m %s\\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

dev-install:  ## Install development dependencies
	pip install -r requirements.txt
	pip install pre-commit pytest pytest-cov black isort flake8 bandit safety mypy
	pre-commit install

test:  ## Run tests
	pytest --cov=. --cov-report=term --cov-report=html

lint:  ## Run linting
	pre-commit run --all-files

format:  ## Format code
	black .
	isort .

security:  ## Run security checks
	bandit -r .
	safety check

analyze:  ## Run code analysis (if available)
	@if [ -f "retroclamp_analyzer.py" ]; then python retroclamp_analyzer.py .; fi

clean:  ## Clean generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/

run:  ## Run the application
	python main.py
"""

    try:
        with open(makefile_path, "w", encoding="utf-8") as f:
            f.write(makefile_content)
        print("✅ Created Makefile:", makefile_path)
    except Exception as e:
        print(f"❌ Failed to create Makefile: {e}")
        sys.exit(1)


def create_scripts_directory(project_root: Path, full_setup: bool = False) -> None:
    """Create scripts directory with quality check scripts."""
    if not full_setup:
        return

    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # Create a simple CHDMAN security check script
    chdman_check = scripts_dir / "chdman_security_check.py"
    chdman_content = """#!/usr/bin/env python3
\"\"\"Basic CHDMAN security check for Retroclamp\"\"\"
import sys
from pathlib import Path

def main():
    issues = []

    # Check core files for shell=True usage
    core_dir = Path("core")
    if core_dir.exists():
        for py_file in core_dir.glob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'shell=True' in content:
                    issues.append(f"Security risk in {py_file}: shell=True usage")
            except Exception:
                continue

    if issues:
        print("CHDMAN Security Issues:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("[OK] CHDMAN security checks passed")

if __name__ == "__main__":
    main()
"""

    # Create plugin validation script
    plugin_check = scripts_dir / "validate_plugins.py"
    plugin_content = """#!/usr/bin/env python3
\"\"\"Basic plugin validation for Retroclamp\"\"\"
import sys
from pathlib import Path

def main():
    tools_dir = Path("tools")
    if not tools_dir.exists():
        print("No tools directory found")
        return

    plugins = [f for f in tools_dir.glob("*.py") if f.name != "__init__.py"]
    if not plugins:
        print("No plugins found")
        return

    issues = []
    for plugin in plugins:
        try:
            with open(plugin, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'PLUGIN_NAME' not in content:
                issues.append(f"{plugin.name}: Missing PLUGIN_NAME")
            if 'def register_tab' not in content:
                issues.append(f"{plugin.name}: Missing register_tab function")

        except Exception:
            continue

    if issues:
        print("Plugin API Issues:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print(f"[OK] All {len(plugins)} plugins validated")

if __name__ == "__main__":
    main()
"""

    try:
        with open(chdman_check, "w", encoding="utf-8") as f:
            f.write(chdman_content)
        chdman_check.chmod(0o755)

        with open(plugin_check, "w", encoding="utf-8") as f:
            f.write(plugin_content)
        plugin_check.chmod(0o755)

        print("✅ Created custom check scripts in scripts/")

    except Exception as e:
        print(f"❌ Failed to create check scripts: {e}")


def create_development_readme(project_root: Path) -> None:
    """Create development guidelines."""
    readme_path = project_root / "DEVELOPMENT.md"

    readme_content = """# Retroclamp Development Guidelines

## Quick Start

```bash
# Setup development environment
make dev-install

# Run quality checks
make lint

# Run tests
make test

# Format code
make format
```

## Quality Gates

This project uses automated quality gates:

- **Pre-commit hooks**: Run automatically before each commit
- **GitHub Actions**: Full CI/CD pipeline on push/PR
- **Quality thresholds**: Minimum standards for code quality

## Development Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and ensure tests pass: `make test`
3. Format code: `make format`
4. Run quality checks: `make lint`
5. Commit (pre-commit hooks will run automatically)
6. Push and create PR

## Component Guidelines

### CHDMAN Integration (core/)
- Use `shell=False` in subprocess calls
- Add proper error handling and timeouts
- Validate all inputs before processing

### Plugin System (tools/)
- Include required metadata: PLUGIN_NAME, PLUGIN_DESCRIPTION, etc.
- Implement `register_tab(parent)` function
- Handle errors gracefully

### GUI Components (gui/)
- Use QThread for long-running operations
- Provide user feedback during operations
- Don't block the GUI thread

## Getting Help

- Run `make help` for available commands
- Check GitHub Actions for CI/CD status
- Review quality reports in PR comments
"""

    try:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print("✅ Created development guidelines:", readme_path)
    except Exception as e:
        print(f"❌ Failed to create development guidelines: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up Retroclamp quality gates")
    parser.add_argument("--install", action="store_true", help="Install quality gates")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include advanced features (custom scripts, extended CI/CD)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.install:
        parser.print_help()
        sys.exit(0)

    project_root = Path.cwd()
    print("🚀 Setting up Retroclamp Quality Gates...")

    # Load appropriate configuration
    if args.full:
        print("📦 Using full configuration with advanced features...")
        config = load_full_config()
    else:
        print("📦 Using basic configuration...")
        config = load_basic_config()

    try:
        # Core setup
        create_pre_commit_config(project_root, config)
        hooks_installed = install_pre_commit_hooks(project_root)
        create_github_actions_workflow(project_root, args.full)
        create_pyproject_toml(project_root)
        create_makefile(project_root)
        create_development_readme(project_root)

        # Advanced features
        if args.full:
            create_scripts_directory(project_root, True)

        # Save configuration
        config_path = project_root / "quality_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print("✅ Saved configuration:", config_path)

        print("\n🎉 Quality Gates setup complete!")
        print("\n📋 Next steps:")

        if not hooks_installed:
            print("  1. Install pre-commit: pip install pre-commit")
            print("  2. Install hooks: pre-commit install")
            print("  3. Run: make dev-install")
        else:
            print("  1. Run: make dev-install")

        print("  X. Run: make lint")
        print(
            "  X. Commit changes: git add . && git commit -m 'feat: setup quality "
            "gates'"
        )

        if args.full:
            print(
                "  X. Copy analysis scripts (retroclamp_analyzer.py, "
                "focused_analysis.py) to project root"
            )

    except KeyboardInterrupt:
        print("\n❌ Setup interrupted")
        sys.exit(1)
    except Exception as e:
        logger.exception("Setup failed")
        print(f"❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
