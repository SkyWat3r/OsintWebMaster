import threading

from osint_app.app import OsmInfoApp


if __name__ == "__main__":
    app = OsmInfoApp()
    url = app.start_local_server()
    opened = app.open_map()
    print(f"OSM Pattern Explorer running at {url}")
    if not opened:
        print("No browser could be opened automatically. Open the URL manually.")
    print("Press Ctrl+C to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping local server...")
    finally:
        app.stop_local_server()
