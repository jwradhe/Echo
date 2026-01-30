import os
from pathlib import Path
from dotenv import load_dotenv
from . import create_app

def main():
    """
    Application entry point with environment detection.
    FLASK_ENV determines behavior:
    - development: Debug enabled, verbose logging
    - testing: Test-specific configuration
    - production: Debug disabled, minimal logging
    """
    # Load environment variables before creating app
    if Path(".env").exists():
        load_dotenv(".env")
    
    env = os.environ.get("FLASK_ENV", "development")
    if env != "development" and env != "testing":
        env_file = f".env.{env}"
        if Path(env_file).exists():
            load_dotenv(env_file, override=True)
    
    app = create_app()
    env = app.config.get("ENV", "development")
    debug = app.config.get("DEBUG", False)
    
    # Only use debug mode in development
    if env != "production":
        print(f"Running in {env.upper()} mode (debug={debug})")
    
    app.run(host="0.0.0.0", port=5001, debug=debug)

if __name__ == "__main__":
    main()
