import os
import subprocess
import sys

# TODO: This is used to run both the UI and the backend. Evaluate if it is necessary
# to use this python script or it is better to run the local app from the UI script
# or from a bash script

# --- Configuration ---
PYTHON_EXECUTABLE = sys.executable
# The command to run FastAPI with Uvicorn. We will add --port dynamically.
BACKEND_COMMAND = [PYTHON_EXECUTABLE, "-m", "api.main"]
BACKEND_CWD = os.path.dirname(os.path.abspath(__file__))


def main():
    try:
        backend_process = subprocess.Popen(BACKEND_COMMAND, cwd=BACKEND_CWD)

        # TODO: open the gui

        backend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down application...")
    finally:
        if backend_process and backend_process.poll() is None:
            backend_process.terminate()
            backend_process.wait()

        print("Application has been shut down gracefully.")


if __name__ == "__main__":
    main()
