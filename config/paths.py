from pathlib import Path

# Get the project root directory (FastAPI/form)
BASE_DIR = Path(__file__).parent.parent

# Templates directory structure
TEMPLATE_DIR = BASE_DIR / "templates"

# Static directory structure
STATIC_DIR = BASE_DIR / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"


