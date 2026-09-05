import pytest
from areos.llm.providers import _azure_call, _custom_call, _ProviderUnavailable

def test_azure_call_blocks_private_ip():
    with pytest.raises(_ProviderUnavailable) as exc:
        _azure_call("fake-key", "http://169.254.169.254/openai", "test", model=None, system=None)
    assert "SSRF blocked" in str(exc.value)

def test_azure_call_blocks_localhost():
    with pytest.raises(_ProviderUnavailable) as exc:
        _azure_call("fake-key", "http://127.0.0.1:8000/openai", "test", model=None, system=None)
    assert "SSRF blocked" in str(exc.value)

def test_custom_call_blocks_private_cidr():
    with pytest.raises(_ProviderUnavailable) as exc:
        _custom_call("fake-key", "http://10.0.0.5:11434", "test", model=None, system=None)
    assert "SSRF blocked" in str(exc.value)

def test_custom_call_blocks_metadata():
    with pytest.raises(_ProviderUnavailable) as exc:
        _custom_call("", "http://169.254.169.254", "test", model=None, system=None)
    assert "SSRF blocked" in str(exc.value)
