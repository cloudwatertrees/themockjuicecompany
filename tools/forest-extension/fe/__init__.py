"""Shared helpers for the forest extension: data I/O, geometry, colour, rendering.
Reuses the Phase B data model and render model from tools/forest-regrade/scripts/tools (art.py, pbart.py, pbrender.py)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'forest-regrade', 'scripts', 'tools'))
