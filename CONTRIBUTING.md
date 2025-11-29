# Contributing to XBridge

Thank you for your interest in contributing to XBridge! We welcome contributions from the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/xbridge.git
   cd xbridge
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/Meaningful-Data/xbridge.git
   ```

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Poetry (for dependency management)
- 7z command-line tool (for taxonomy loading)

### Installation

1. Install Poetry if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install project dependencies:
   ```bash
   poetry install
   ```

3. Activate the virtual environment:
   ```bash
   poetry shell
   ```

### Setting up Pre-commit Hooks (Optional but Recommended)

We use Ruff for linting and formatting, and MyPy for type checking. While we don't have automated pre-commit hooks, you should run these before committing:

```bash
# Run Ruff linting
ruff check src/xbridge tests/

# Run Ruff formatting
ruff format src/xbridge tests/

# Run MyPy type checking
mypy src/xbridge
```

## How to Contribute

### Types of Contributions

We welcome many types of contributions:

- Bug fixes
- New features
- Documentation improvements
- Performance improvements
- Test coverage improvements
- Code refactoring
- Translation improvements

### Contribution Workflow

1. **Check existing issues**: Before starting work, check if there's already an issue for what you want to do
2. **Create an issue**: If no issue exists, create one to discuss your proposed changes
3. **Create a branch**: Create a feature branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```
4. **Make your changes**: Implement your changes following our code style guidelines
5. **Test your changes**: Ensure all tests pass and add new tests if needed
6. **Commit your changes**: Write clear, descriptive commit messages
7. **Push to your fork**: Push your changes to your GitHub fork
8. **Submit a pull request**: Open a PR against the `main` branch

## Code Style Guidelines

### Python Code Style

We follow these standards:

- **PEP 8**: Python Enhancement Proposal 8 style guide
- **Ruff**: For linting and formatting (configuration in `pyproject.toml`)
- **MyPy**: For static type checking with strict mode enabled
- **Type hints**: All functions should have type annotations

### Code Quality Standards

- **Line length**: Maximum 100 characters
- **Docstrings**: All public modules, functions, classes, and methods should have docstrings
- **Type hints**: Required for all function signatures
- **Complexity**: Maximum McCabe complexity of 20

### Example

```python
from typing import Optional
from pathlib import Path


def example_function(
    input_path: Path,
    output_path: Optional[Path] = None,
    validate: bool = True,
) -> bool:
    """
    Brief description of what this function does.

    :param input_path: Description of input_path parameter
    :param output_path: Description of output_path parameter
    :param validate: Description of validate parameter
    :return: Description of return value
    """
    # Implementation
    pass
```

## Testing

### Running Tests

Run the test suite using pytest:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=xbridge --cov-report=html

# Run specific test file
pytest tests/test_specific.py

# Run with verbose output
pytest -v
```

### Writing Tests

- All new features should include tests
- Bug fixes should include regression tests
- Aim for high test coverage (we strive for >80%)
- Use descriptive test names that explain what is being tested
- Follow the Arrange-Act-Assert pattern

Example test:

```python
def test_convert_instance_creates_output_file(tmp_path):
    """Test that convert_instance creates an output file."""
    # Arrange
    input_path = "tests/data/sample_instance.xml"
    output_path = tmp_path / "output"

    # Act
    result = convert_instance(input_path, output_path)

    # Assert
    assert result.exists()
    assert result.suffix == ".zip"
```

## Documentation

### Documentation Standards

- Use reStructuredText (.rst) format for documentation
- Follow Sphinx documentation conventions
- Include docstrings for all public APIs
- Update relevant documentation when changing functionality

### Building Documentation Locally

```bash
cd docs
sphinx-build -b html . _build
```

The documentation will be available in `docs/_build/index.html`.

### Documentation Types

- **API Documentation**: Auto-generated from docstrings
- **Tutorials**: Step-by-step guides for common tasks
- **How-to Guides**: Solutions to specific problems
- **Technical Notes**: Deep dives into architecture and design

## Submitting Changes

### Pull Request Process

1. **Update documentation**: Ensure documentation is updated for any changed functionality
2. **Update CHANGELOG**: Add an entry to the "Unreleased" section of [CHANGELOG.md](CHANGELOG.md)
3. **Ensure tests pass**: All tests must pass before PR can be merged
4. **Code review**: At least one maintainer must review and approve your PR
5. **CI checks**: All CI checks (testing, linting, type checking) must pass

### Pull Request Guidelines

- **Title**: Use a clear, descriptive title
- **Description**: Explain what changes you made and why
- **Link issues**: Reference any related issues (e.g., "Fixes #123")
- **Small PRs**: Keep PRs focused on a single concern when possible
- **Commits**: Use clear commit messages following conventional commits format

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(converter): add support for DORA CSV conversion

fix(instance): handle None values in decimals field

docs(readme): update installation instructions
```

## Reporting Bugs

### Before Reporting

1. Check the [issue tracker](https://github.com/Meaningful-Data/xbridge/issues) for existing reports
2. Try to reproduce with the latest version
3. Gather relevant information (error messages, input files, etc.)

### Bug Report Should Include

- **Description**: Clear description of the bug
- **Steps to reproduce**: Minimal steps to reproduce the issue
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**: Python version, OS, XBridge version
- **Error messages**: Full error messages and stack traces
- **Sample data**: If possible, provide sample input files (without sensitive data)

## Suggesting Enhancements

We welcome feature suggestions! When suggesting an enhancement:

1. **Check existing issues**: See if someone else has suggested it
2. **Provide context**: Explain the use case and why it's valuable
3. **Describe the solution**: How you envision the feature working
4. **Consider alternatives**: What other approaches might work?

## Questions?

If you have questions about contributing:

- Open a [GitHub Discussion](https://github.com/Meaningful-Data/xbridge/discussions)
- Email us at info@meaningfuldata.eu
- Check our [documentation](https://docs.xbridge.meaningfuldata.eu)

## License

By contributing to XBridge, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for contributing to XBridge!
