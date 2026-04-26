"""
ByteBuddies – Sovelluksen käynnistys.

Käynnistää Streamlit-sovelluksen (app.py) yhdellä komennolla:
    uv run python main.py
"""

import subprocess
import sys


def main():
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.headless", "true"],
    )


if __name__ == "__main__":
    main()
    #