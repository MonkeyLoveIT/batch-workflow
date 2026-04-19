"""
pytest configuration - load plugins before any tests run.
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load all plugins
import plugins
