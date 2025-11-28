# cli-speeder

**Make your Python CLIs start instantly (10x-100x faster).**
Python scripts are notoriously slow to start because they import heavy libraries (like `pandas`, `torch`, `boto3`, `pydantic`) at the top level, even if the user only runs a simple command like `--help`.

`cli-speeder` fixes this with **zero code refactoring**.

## Installation

```
pip install cli-speeder
```

## Usage
There are two ways to use this.

### Method 1: The "One-Liner" (Recommended)
Add this **once** at the very top of your script (before your heavy imports).

```python
from cli_speeder import speed_up_modules
# Magic: Forces these modules to load lazily
speed_up_modules(["pandas", "tensorflow", "boto3"])

# --- Your normal code stays exactly the same! ---
import pandas as pd      \# 0ms (Instant)
import tensorflow as tf  \# 0ms (Instant)
import boto3             \# 0ms (Instant)

def process_data():
\# The libraries only actually load HERE, when you use them.
df = pd.read_csv("data.csv")
```

### Method 2: Manual Proxy (Granular Control)
If you want specific control over exactly which object is lazy.

```python
from cli_speeder import lazy_import, lazy_from_import

# Replace 'import pandas as pd' with:
pd = lazy_import("pandas")

# Replace 'from pandas import DataFrame' with:
DataFrame = lazy_from_import("pandas", "DataFrame")

```

## Benchmarks

Time to run `python script.py --help`:

| Library | Standard Import | With `cli-speeder` |
| :--- | :--- | :--- |
| **Pandas** | ~0.8s | **< 0.01s** |
| **Torch** | ~2.5s | **< 0.01s** |
| **Boto3** | ~0.5s | **< 0.01s** |

## Debugging / Production Safety

Lazy loading is great for CLIs, but sometimes (like in production workers) you might want standard behavior to catch `ImportError` immediately.

You can force all imports to happen immediately (disable lazy loading) by setting an environment variable:

```
export CLI_SPEEDER_EAGER=1
python my_script.py
```

## License
**cli_speeder** is licensed under the Apache License 2.0. See the LICENSE file for more details.

