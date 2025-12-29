"""Flask application entry point."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("\n" + "="*70)
    print("MULTI-ASSET STRATEGY DASHBOARD")
    print("="*70)
    print("\nStarting Flask development server...")
    print("Dashboard will be available at: http://127.0.0.1:5000")
    print("\nPages:")
    print("  - Dashboard Home:      http://127.0.0.1:5000/")
    print("  - Performance:         http://127.0.0.1:5000/performance")
    print("  - Methodology:         http://127.0.0.1:5000/methodology")
    print("\nPress CTRL+C to stop the server")
    print("="*70 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5000)
