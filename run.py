"""Start the development server: python run.py"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Never run with debug=True on a public server: it exposes an interactive shell.
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
