import os
import sys

# Bridge root `app` package to `backend/app`
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND_DIR = os.path.join(_ROOT_DIR, "backend")
_BACKEND_APP_DIR = os.path.join(_BACKEND_DIR, "app")

if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

if _BACKEND_APP_DIR not in __path__:
    __path__.append(_BACKEND_APP_DIR)
