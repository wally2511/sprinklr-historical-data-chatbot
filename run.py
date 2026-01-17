#!/usr/bin/env python3
"""
Convenience script to run the Streamlit app.

Usage:
    python run.py

Or run directly with:
    streamlit run src/app.py
"""

import subprocess
import sys


def main():
    """Run the Streamlit app."""
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "src/app.py",
            "--server.headless", "true"
        ], check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except subprocess.CalledProcessError as e:
        print(f"Error running app: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
