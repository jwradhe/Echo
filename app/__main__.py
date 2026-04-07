def main():
    """
    Application entry point with environment detection.
    FLASK_ENV determines behavior:
    - development: Debug enabled, verbose logging
    - testing: Test-specific configuration
    - production: Debug disabled, minimal logging
    """
    import os
    from . import create_app
    app = create_app()
    env = app.config.get("ENV", "development")
    debug = app.config.get("DEBUG", False)

    # Start Prometheus metrics server on port 8080 in a background thread.
    # Using a separate server avoids conflicts with Flask's debug reloader.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not debug:
        from prometheus_client import start_http_server
        start_http_server(8080)

    port = int(os.environ.get("PORT", "5000"))

    # Only use debug mode in development
    if env != "production":
        print(f"Running in {env.upper()} mode (debug={debug}, port={port})")

    app.run(host="0.0.0.0", port=port, debug=debug)

if __name__ == "__main__":
    main()
