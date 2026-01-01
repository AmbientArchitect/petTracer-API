# VS Code Quick Start Guide

## Running the Example Script

### Method 1: Using .env file (Recommended for development)

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```
   PETTRACER_USERNAME=your_username
   PETTRACER_PASSWORD=your_password
   ```

3. In VS Code:
   - Open `examples/class_based_example.py`
   - Press **F5**
   - Select **"Python: Run with .env"** from the dropdown

### Method 2: From Terminal

```bash
# Activate virtual environment (opens new terminal with PYTHONPATH already set)
source .venv/bin/activate

# Set your credentials
export PETTRACER_USERNAME="your_username"
export PETTRACER_PASSWORD="your_password"

# Run the script
python examples/class_based_example.py
```

### Method 3: Prompted Credentials

1. Open `examples/class_based_example.py`
2. Press **F5**
3. Select **"Python: Class-based Example"**
4. VS Code will prompt for credentials

## Running Tests

### From VS Code Testing Panel

1. Click the **Testing** icon in the sidebar (beaker icon)
2. Tests will auto-discover from `tests/` directory
3. Click the play button next to any test to run it
4. Use the debug icon to debug tests with breakpoints

### From Terminal

```bash
source .venv/bin/activate

# Run all tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_client.py -v

# Run with coverage
pytest --cov=pettracer tests/
```

## Debugging

1. Set breakpoints by clicking left of line numbers
2. Press **F5** to start debugging
3. Use the Debug toolbar:
   - Continue (F5)
   - Step Over (F10)
   - Step Into (F11)
   - Step Out (Shift+F11)

## Troubleshooting

### "ModuleNotFoundError: No module named 'pettracer'"

**Solution**: The workspace automatically sets PYTHONPATH for new terminals. Either:
- Open a new terminal in VS Code (Terminal > New Terminal)
- Or manually set: `export PYTHONPATH="${PWD}"`

### "Please set PETTRACER_USERNAME and PETTRACER_PASSWORD"

**Solution**: The example requires credentials. Use one of the three methods above.

### Tests not showing in Testing panel

**Solution**: 
1. Ensure pytest is installed: `pip install -r requirements-dev.txt`
2. Reload VS Code: Command Palette > "Developer: Reload Window"
3. Check Python interpreter is set to `.venv/bin/python`

## File Structure

```
petTracer API/
├── .vscode/
│   ├── settings.json      # Python interpreter, PYTHONPATH, pytest config
│   └── launch.json        # Debug configurations
├── .env.example           # Template for credentials
├── .env                   # Your credentials (gitignored)
├── pettracer/             # Main package
│   ├── __init__.py
│   ├── client.py          # PetTracerClient and PetTracerDevice classes
│   └── types.py           # Data classes
├── examples/
│   └── class_based_example.py
└── tests/
    └── test_client.py
```
