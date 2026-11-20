# Contributing to Urban Green and Blue Change Monitor

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating, you agree to uphold our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, browser, Python/Node versions)
   - Screenshots if applicable

### Suggesting Features

1. Check existing feature requests
2. Create a feature request issue with:
   - Clear description of the feature
   - Use cases and benefits
   - Potential implementation approach
   - Any related issues or PRs

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Run tests: `pytest` (backend) and `npm test` (frontend)
5. Run linters: `ruff check .` and `npm run lint`
6. Commit with clear messages
7. Push and create a Pull Request

## Development Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
cp ../.env.example .env
# Edit .env with your GEE credentials
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend
cd backend
pytest tests/ -v --cov=.

# Frontend
cd frontend
npm run test

# E2E
cd frontend
npx playwright test
```

## Code Style

### Python (Backend)

- Follow PEP 8 (enforced by Ruff)
- Type hints required for all public functions
- Docstrings for all public classes/functions (Google style)
- Max line length: 100 characters

### TypeScript/React (Frontend)

- Follow Airbnb style guide (enforced by ESLint)
- Functional components with hooks
- TypeScript strict mode enabled
- Use Tailwind utility classes
- Accessible components (ARIA, keyboard navigation)

## Commit Messages

Follow Conventional Commits:

```
type(scope): short description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

Example:
```
feat(backend): add lake detection module

- Implement lake detection using connected components
- Add shrinkage alert threshold parameter
- Export lake statistics to CSV

Closes #42
```

## Testing Guidelines

- Write tests for new features
- Maintain >80% code coverage
- Unit tests for pure functions
- Integration tests for API endpoints
- E2E tests for critical user flows
- Mock external dependencies (GEE, APIs)

## Documentation

- Update README.md for user-facing changes
- Update API docs (docs/api.md) for endpoint changes
- Update methodology.md for algorithm changes
- Add docstrings for new public APIs
- Update CHANGELOG.md (if exists)

## GEE-Specific Guidelines

- Never commit GEE credentials
- Use service accounts for deployed environments
- Test quota usage locally before deploying
- Document any new GEE assets or collections used
- Consider computational cost of new operations

## Release Process

1. Update version in `pyproject.toml` and `package.json`
2. Update CHANGELOG.md
3. Create Git tag: `git tag v1.0.0`
4. GitHub Actions will build and deploy
5. Verify deployment
5. Announce release

## Questions?

Open an issue or start a discussion. We're happy to help!