import json
import sys
from pathlib import Path

# Add project root to sys.path to allow importing app module
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.main import app

def generate_openapi():
    # Generate OpenAPI schema
    openapi_schema = app.openapi()
    
    # Save to backend directory
    backend_output = backend_dir / "openapi.json"
    with open(backend_output, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    print(f"Generated OpenAPI schema at {backend_output}")

    # Save to web directory (if it exists)
    web_dir = backend_dir.parent / "coding-contest-web"
    if web_dir.exists():
        web_output = web_dir / "openapi.json"
        with open(web_output, "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        print(f"Generated OpenAPI schema at {web_output}")

if __name__ == "__main__":
    generate_openapi()
