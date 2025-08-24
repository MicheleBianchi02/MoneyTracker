import argparse
import os
import socket
import subprocess
import sys

# --- Configuration ---
PYTHON_EXECUTABLE = sys.executable
# The command to run FastAPI with Uvicorn. We will add --port dynamically.
BACKEND_COMMAND = [
    PYTHON_EXECUTABLE,
    "-m",
    "uvicorn",
    "src.api.main:app",
    "--host",
    "127.0.0.1",
]
BACKEND_CWD = os.path.dirname(os.path.abspath(__file__))


def find_free_port():
    """Finds a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]  # Return the port number


def main():
    try:
        backend_port = find_free_port()
        print(f"Found free port on localhost: {backend_port}")

        parser = argparse.ArgumentParser(description="My Application")
        parser.add_argument(
            "-cli", action="store_true", help="Run the application in Terminal mode"
        )
        args = parser.parse_args()

        use_cli = True if args.cli else False

        # Remove log by uvicorn (API) when in cli mode, otherwise they will be printed
        # with the other things from the tui
        if use_cli:
            BACKEND_COMMAND.extend(["--log-level", "critical"])

        print("Starting backend.....")
        final_command = BACKEND_COMMAND + ["--port", str(backend_port)]
        backend_process = subprocess.Popen(final_command, cwd=BACKEND_CWD)
        print(f"Backend started with PID: {backend_process.pid} on port {backend_port}")

        if use_cli:
            tui_command = [PYTHON_EXECUTABLE, "-m", "src.tui.main"]
            tui_process = subprocess.Popen(tui_command, cwd=BACKEND_CWD)

        else:
            # TODO: Add UI startup
            pass

        if use_cli:
            tui_process.wait()
        else:
            backend_process.wait()

    except KeyboardInterrupt:
        print("\nShutting down application...")
    finally:
        if backend_process and backend_process.poll() is None:
            backend_process.terminate()
            backend_process.wait()

        if use_cli:
            if tui_process and tui_process.poll() is None:
                tui_process.terminate()
                tui_process.wait()

        print("Application has been shut down gracefully.")


if __name__ == "__main__":
    main()
