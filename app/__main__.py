def main():
    """
    Application entry point with environment detection.
    FLASK_ENV determines behavior:
    - development: Debug enabled, verbose logging
    - testing: Test-specific configuration
    - production: Debug disabled, minimal logging
    """
    from . import create_app
    app = create_app()
    env = app.config.get("ENV", "development")
    debug = app.config.get("DEBUG", False)
    
    # Only use debug mode in development
    if env != "production":
        print(f"Running in {env.upper()} mode (debug={debug})")
    
    app.run(host="0.0.0.0", port=5000, debug=debug)

if __name__ == "__main__":
    main()
