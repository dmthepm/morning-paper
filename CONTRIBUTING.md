# Contributing to Morning Paper

Thanks for your interest in contributing. Morning Paper is a focused CLI tool.
Contributions that keep it simple, portable, and useful are welcome.

## Getting Started

Clone the repo and install in development mode:

    git clone https://github.com/dmthepm/morning-paper.git
    cd morning-paper
    pip install -e ".[dev]"
    python -m pytest tests/
    morning-paper doctor

## Development Workflow

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add or update tests when behavior changes
4. Run the test suite and any relevant CLI checks
5. Open a pull request against `main`

## Good Contributions

- New source plugins that keep the default install simple
- Article extraction improvements
- PDF rendering fixes
- Documentation improvements
- Bug fixes with reproduction steps

## Please Discuss First

- New CLI commands
- New dependencies
- Architectural changes
- Anything that adds complexity

Open an issue before starting large work so we can align on direction.

## Code Style

- Keep it simple. Morning Paper is intentionally minimal.
- No unnecessary abstractions
- Type hints are appreciated but not required
- Docstrings on public functions

## Commit Messages

Use clear, descriptive commit messages:

- fix: handle RSS feeds with missing dates
- feat: add Substack-specific extractor
- docs: update quickstart section

## Running Tests

    python -m pytest tests/
    python -m pytest tests/test_build.py
    morning-paper --version
    morning-paper doctor

## Code of Conduct

By participating in this project, you agree to follow
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Questions?

- Open an issue for bugs or feature discussion
- Join the community at [Main Branch](https://skool.com/main) for broader discussion
