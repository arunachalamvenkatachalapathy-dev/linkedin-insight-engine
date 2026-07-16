import sys
import os

# Align root paths for EcoPulse orchestrator execution
ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from scripts.orchestrator import main

if __name__ == "__main__":
    main()
