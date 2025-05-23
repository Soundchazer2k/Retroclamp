# Retroclamp Development Guidelines

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
