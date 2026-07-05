# Ensure root is added to sys.path by pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
