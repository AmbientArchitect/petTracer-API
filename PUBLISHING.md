# Publishing to PyPI

This guide explains how to publish the pettracer-client package to PyPI.

## Prerequisites

1. Install build tools:
```bash
pip install --upgrade build twine
```

2. Create accounts on:
   - PyPI: https://pypi.org/account/register/
   - TestPyPI (optional, for testing): https://test.pypi.org/account/register/

## Build the Package

1. Make sure version is updated in `pettracer/__init__.py`

2. Clean old builds:
```bash
rm -rf dist/ build/ *.egg-info/
```

3. Build the package:
```bash
python -m build
```

This creates `.tar.gz` (source) and `.whl` (wheel) files in `dist/`.

## Test on TestPyPI (Optional but Recommended)

1. Upload to TestPyPI:
```bash
python -m twine upload --repository testpypi dist/*
```

2. Install from TestPyPI to test:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple pettracer-client
```

## Publish to PyPI

1. Upload to PyPI:
```bash
python -m twine upload dist/*
```

2. Enter your PyPI username and password when prompted.

3. Verify the upload at: https://pypi.org/project/pettracer-client/

## Using API Tokens (Recommended)

Instead of username/password, use API tokens for better security:

1. Generate token at: https://pypi.org/manage/account/token/

2. Create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-AgEIcH...YOUR_TOKEN_HERE
```

3. Upload:
```bash
python -m twine upload dist/*
```

## Version Bumping

When releasing a new version:

1. Update version in `pettracer/__init__.py`
2. Update badges in README.md (if needed)
3. Create git tag:
```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

## Automated Publishing with GitHub Actions

Consider setting up GitHub Actions for automatic publishing on tag creation. Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: python -m twine upload dist/*
```

Add your PyPI API token as `PYPI_API_TOKEN` in GitHub Secrets.

## Pre-Release Checklist

- [ ] All tests pass (`pytest`)
- [ ] Version number updated
- [ ] README.md is up to date
- [ ] CHANGELOG updated (if exists)
- [ ] Git committed and tagged
- [ ] Built and tested locally

## Troubleshooting

**Error: "File already exists"**
- Cannot re-upload same version
- Bump version number in `__init__.py`

**Error: "Invalid distribution"**
- Check `pyproject.toml` syntax
- Ensure all required files are included

**Import errors after install**
- Check `MANIFEST.in` includes all needed files
- Verify `pyproject.toml` packages list is correct
