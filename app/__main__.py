import os
from . import create_app

def main():
    app = create_app()
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5001, debug=debug)

if __name__ == "__main__":
    main()
