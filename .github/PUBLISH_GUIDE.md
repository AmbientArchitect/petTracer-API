# GitHub Actions Setup Guide

This repository includes GitHub Actions workflows for automated testing, releases, and PyPI publishing.

## Workflows

### 1. Tests (`test.yml`)
**Triggers:** Push to main, Pull requests, Manual
- Runs on every push and PR
- Tests package imports and async functionality
- Verifies code quality

### 2. Build and Publish to PyPI (`publish.yml`)
**Triggers:** Version tags (v*), Manual
- Runs tests
- Builds the package
- Publishes to PyPI using trusted publishing

### 3. Create Release (`release.yml`)
**Triggers:** Version tags (v*)
- Creates a GitHub release
- Generates release notes from commits
- Attaches changelog

## Setup Instructions

### 1. Configure PyPI Trusted Publishing (Recommended)

PyPI now supports trusted publishing which doesn't require storing API tokens:

1. Go to [PyPI Account Publishing](https://pypi.org/manage/account/publishing/)
2. Add a new pending publisher:
   - **PyPI Project Name:** `pettracer-client`
   - **Owner:** `AmbientArchitect`
   - **Repository:** `petTracer-API`
   - **Workflow:** `publish.yml`
   - **Environment:** `pypi`

3. The first time you create a release, PyPI will automatically trust the workflow

### 2. Alternative: Using API Token

If you prefer using an API token:

1. Go to [PyPI Account Settings](https://pypi.org/manage/account/token/)
2. Create a new API token (scope: entire account or specific to pettracer-client)
3. Copy the token (starts with `pypi-`)
4. Go to your GitHub repository → Settings → Secrets and variables → Actions
5. Create a new repository secret:
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI token
6. Update [.github/workflows/publish.yml](.github/workflows/publish.yml):
   ```yaml
   - name: Publish to PyPI
     uses: pypa/gh-action-pypi-publish@release/v1
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
   ```

## Creating a Release

### 1. Update Version Number

Edit [pyproject.toml](../pyproject.toml):
```toml
version = "0.1.1"  # Increment version
```

### 2. Commit Changes

```bash
git add pyproject.toml
git commit -m "Bump version to 0.1.1"
git push
```

### 3. Create and Push Tag

```bash
# Create annotated tag with release notes
git tag -a v0.1.1 -m "Release v0.1.1

- Converted to async/await with aiohttp
- Added Home Assistant session support
- Improved error handling
"

# Push tag to trigger workflows
git push origin v0.1.1
```

### 4. Workflows Will Automatically:
- Run tests
- Build the package
- Create a GitHub release
- Publish to PyPI

## Manual Publishing

To publish manually without creating a release:

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check the build
twine check dist/*

# Upload to PyPI (requires API token or credentials)
twine upload dist/*
```

## Test PyPI (Optional)

To test the publishing process without affecting the real PyPI:

1. Create account on [TestPyPI](https://test.pypi.org/)
2. Get API token from TestPyPI
3. Upload to TestPyPI:
   ```bash
   twine upload --repository testpypi dist/*
   ```

## Monitoring Workflow Runs

- View workflow runs: [Actions Tab](../../actions)
- Check PyPI releases: https://pypi.org/project/pettracer-client/
- View GitHub releases: [Releases Page](../../releases)

## Troubleshooting

### Publish fails with "File already exists"
- You're trying to publish a version that already exists on PyPI
- Increment the version number in `pyproject.toml`

### Tests fail
- Check the [Actions tab](../../actions) for detailed error logs
- Fix issues locally and push changes
- The publish workflow won't run until tests pass

### PyPI trusted publishing not working
- Ensure the workflow name, repository owner, and environment name exactly match
- The environment name in the workflow must be `pypi`
- Wait a few minutes after configuring trusted publishing

## Best Practices

1. **Always test locally first:**
   ```bash
   python -m build
   twine check dist/*
   ```

2. **Use semantic versioning:**
   - `v0.1.0` → `v0.1.1` (patch: bug fixes)
   - `v0.1.0` → `v0.2.0` (minor: new features, backward compatible)
   - `v0.1.0` → `v1.0.0` (major: breaking changes)

3. **Write meaningful release notes in the tag message**

4. **Test the package after publishing:**
   ```bash
   pip install --upgrade pettracer-client
   python -c "from pettracer import PetTracerClient; print('OK')"
   ```
