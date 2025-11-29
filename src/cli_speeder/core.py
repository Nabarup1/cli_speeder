import importlib
import importlib.util
import importlib.abc
import sys
import os
import threading
from typing import Any, Callable, Optional, TypeVar, Generic, List, Set

_EAGER_MODE = os.environ.get("CLI_SPEEDER_EAGER", "0") == "1"

T = TypeVar("T")

class _LazyProxy(Generic[T]):
    __slots__ = ("_loader_func", "_target", "__weakref__")

    def __init__(self, loader_func: Callable[[], T]):
        object.__setattr__(self, "_loader_func", loader_func)
        object.__setattr__(self, "_target", None)
        if os.environ.get("CLI_SPEEDER_EAGER", "0") == "1":
            self._ensure_loaded()

    def _ensure_loaded(self) -> T:
        if self._target is None:
            target = self._loader_func()
            object.__setattr__(self, "_target", target)
        return self._target

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ensure_loaded(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._ensure_loaded(), name, value)

    def __delattr__(self, name: str) -> None:
        delattr(self._ensure_loaded(), name)

    def __repr__(self) -> str:
        if self._target is None:
            return f"<LazyProxy (not loaded)>"
        return repr(self._target)
    
    def __str__(self) -> str:
        if self._target is None:
             return self.__repr__()
        return str(self._target)

    def __call__(self, *args, **kwargs) -> Any:
        return self._ensure_loaded()(*args, **kwargs)
    
    def __getitem__(self, key: Any) -> Any:
        return self._ensure_loaded()[key]

    @property
    def __doc__(self) -> Optional[str]:
        return self._ensure_loaded().__doc__

class LazyModuleProxy(_LazyProxy[Any]):
    __slots__ = ("_module_name",)
    def __init__(self, module_name: str, package: Optional[str] = None):
        def loader():
            return importlib.import_module(module_name, package=package)
        object.__setattr__(self, "_module_name", module_name)
        super().__init__(loader)

    def __repr__(self) -> str:
        if self._target is None:
            return f"<LazyModuleProxy: '{self._module_name}' (not loaded)>"
        return repr(self._target)

class LazyObjectProxy(_LazyProxy[Any]):
    __slots__ = ("_module_name", "_object_name")
    def __init__(self, module_name: str, object_name: str, package: Optional[str] = None):
        def loader():
            mod = importlib.import_module(module_name, package=package)
            return getattr(mod, object_name)
        object.__setattr__(self, "_module_name", module_name)
        object.__setattr__(self, "_object_name", object_name)
        super().__init__(loader)

    def __repr__(self) -> str:
        if self._target is None:
            return f"<LazyObjectProxy: '{self._module_name}.{self._object_name}' (not loaded)>"
        return repr(self._target)

def lazy_import(name: str, package: Optional[str] = None) -> Any:
    return LazyModuleProxy(name, package)

def lazy_from_import(module_name: str, class_name: str, package: Optional[str] = None) -> Any:
    return LazyObjectProxy(module_name, class_name, package)



class _LazyFinder(importlib.abc.MetaPathFinder):
    """
    A custom importer that intercepts specific module names and 
    returns a LazyLoader.
    
    Uses thread-local storage to prevent recursion during delegation.
    """
    def __init__(self, names: List[str]):
        self.names = set(names)
        self._local = threading.local()

    def find_spec(self, fullname, path, target=None):
        # RECURSION CHECK:
        # If we are already inside a find_spec call on this thread, ignore this call.
        if getattr(self._local, "in_lookup", False):
            return None

        # We only care if the TOP LEVEL package matches our list
        root_pkg = fullname.split(".")[0]
        if root_pkg not in self.names:
            return None

        # DELEGATION (With Guard):
        try:
            self._local.in_lookup = True  # LOCK
            
            # Iterate over other finders manually
            spec = None
            for finder in sys.meta_path:
                if finder is self: 
                    continue
                try:
                    if hasattr(finder, "find_spec"):
                        spec = finder.find_spec(fullname, path, target)
                        if spec:
                            break
                except (ImportError, AttributeError):
                    continue

            if spec is None:
                return None

            # WRAP IN LAZY LOADER
            # Only wrap if it has a loader and isn't already lazy
            if spec.loader and not isinstance(spec.loader, importlib.util.LazyLoader):
                spec.loader = importlib.util.LazyLoader(spec.loader)
            
            return spec
            
        finally:
            self._local.in_lookup = False  # UNLOCK

# Global reference
_INSTALLED_FINDER = None

def speed_up_modules(modules: List[str]):
    """
    Forces the listed modules to be lazy-loaded globally.
    
    Args:
        modules: List of top-level package names (e.g., ["pandas", "boto3"])
    """
    global _INSTALLED_FINDER
    
    unsafe = {"numpy", "torch", "pydantic"}
    safe_modules = [m for m in modules if m not in unsafe]
    
    if _INSTALLED_FINDER is None:
        _INSTALLED_FINDER = _LazyFinder(safe_modules)
        sys.meta_path.insert(0, _INSTALLED_FINDER)
    else:
        _INSTALLED_FINDER.names.update(safe_modules)


# @contextmanager
# def lazy_imports():
#     """
#     Context manager syntax.
    
#     Usage:
#         with lazy_imports():
#             import pandas as pd
#             import numpy as np
#     """
#     # We can't easily make 'with' work without hacking sys.meta_path anyway,
#     # but typically users prefer the 'speed_up_modules' approach for global scripts.
#     # For a true 'local' context manager, we'd need AST manipulation which is unsafe.
#     # Instead, we'll use the same MetaPath trick but only for the duration of the block.
#     raise NotImplementedError("Use 'speed_up_modules([...])' at the top of your file instead. It's safer and cleaner.")
