# Contributing to GrokFlow CLI

Thank you for your interest in contributing to GrokFlow CLI!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/grokflow-cli.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `python3 test_cli_e2e.py`
6. Commit: `git commit -m "feat: Add your feature"`
7. Push: `git push origin feature/your-feature`
8. Open a Pull Request

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run tests
python3 test_cli_e2e.py

# Run demos
./demo_cli_automated.sh
```

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public functions
- Add tests for new features

## Testing

- All features must have tests
- E2E tests must pass: `python3 test_cli_e2e.py`
- Aim for >90% code coverage

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test changes
- `chore:` Maintenance tasks

## Questions?

Open an issue or start a discussion!
