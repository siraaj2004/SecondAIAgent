"""
Second AI Agent — entry point.

Runs the approval-only workflow web server (UI + API).
No Instagram login or integration is used anywhere.
"""

from server import main

if __name__ == "__main__":
    main()
