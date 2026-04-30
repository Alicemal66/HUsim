# Contributing to HUsim

Thank you for your interest in contributing to HUsim.

## How to Contribute

### Reporting Issues

Open an issue on GitHub with:
- A clear description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- Your OS, Python version, and Node.js version

### Submitting Pull Requests

1. Fork the repository on GitHub
2. Create a feature branch from `main`:
   ```
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following the code style guidelines below
4. Commit your changes using the commit format below
5. Push to your fork and open a pull request against `main`
6. Describe what your PR changes and why

## Development Setup

See the Quick Start section in README.md for installation instructions.

Backend runs on `http://localhost:8000`, frontend on `http://localhost:5173`.

## Code Style

**Python (backend)**
- Follow PEP 8
- Use type hints for all function signatures
- Run `flake8` before committing

**TypeScript (frontend)**
- Follow the ESLint config in the project
- Use functional React components with hooks
- Run `npm run lint` before committing

**Comments**
- All code comments must be written in English
- Only comment when the WHY is non-obvious — do not describe what the code does

## Commit Message Format

Use one of these prefixes:

```
Add: short description of new feature
Fix: short description of bug fix
Update: short description of enhancement
Remove: short description of removed code
```

Examples:
```
Add: fog visibility distance parameter to weather optimizer
Fix: ORCA velocity calculation for vehicles at rest
Update: PDF report layout to include weather summary table
Remove: unused legacy frame buffer logic
```

## Branch Naming

```
feature/short-description
fix/short-description
update/short-description
```
