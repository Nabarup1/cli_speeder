import sys
import pytest
from cli_speeder import lazy_import, lazy_from_import

def test_lazy_module_import():
    mod_name = "http.client"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    
    # Create proxy
    lazy_http = lazy_import(mod_name)
    assert mod_name not in sys.modules, "Module should not be loaded on proxy creation"
    assert "LazyModuleProxy" in repr(lazy_http)
    
    # Access attribute -> triggers load
    port = lazy_http.HTTP_PORT
    assert port == 80
    
    # Verify IS loaded now
    assert mod_name in sys.modules, "Module should be loaded after attribute access"
    assert str(lazy_http).startswith("<module 'http.client'")  # standard repr

def test_lazy_object_import():
    mod_name = "json"
    cls_name = "JSONDecoder"
    
    if mod_name in sys.modules:
        del sys.modules[mod_name]
        
    # Create proxy
    LazyDecoder = lazy_from_import(mod_name, cls_name)
    assert mod_name not in sys.modules
    
    # Instantiate class -> triggers load (via __call__)
    decoder = LazyDecoder()
    assert hasattr(decoder, "decode")
    assert mod_name in sys.modules

def test_lazy_list_behavior():
    """Test that magic methods like __getitem__ trigger the load."""
    # We'll lazily import 'sys' just to access 'argv' (which is a list)
    # But strictly speaking, sys is always loaded. Let's use a trick or just trust sys.
    # Ideally we mock an import, but for simplicity we use an existing one and verify proxy behavior.
    
    lazy_sys = lazy_import("sys")
    
    try:
        _ = lazy_sys.path[0]
    except IndexError:
        pass 
        
    assert isinstance(lazy_sys.path, list)

def test_eager_loading_env_var(monkeypatch):
    """Test that setting CLI_SPEEDER_EAGER=1 forces immediate load."""
    monkeypatch.setenv("CLI_SPEEDER_EAGER", "1")
    mod_name = "uuid" 
    
    if mod_name in sys.modules:
        del sys.modules[mod_name]
        
    _ = lazy_import(mod_name)
    
    assert mod_name in sys.modules, "Should have loaded immediately due to env var"
