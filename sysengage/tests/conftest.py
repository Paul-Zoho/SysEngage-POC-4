"""
Root conftest.py for SysEngage test suite.

Adds sysengage/ to sys.path so imports work without package installation.
"""

import os
import sys

# Allow imports from the sysengage/ source root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
