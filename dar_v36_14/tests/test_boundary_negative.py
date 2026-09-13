import pytest
from dar.boundary import BoundaryDenied, PrivilegedDispatcher


def test_no_public_execute_endpoint(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    assert not hasattr(d, "execute")


def test_undeclared_effect_is_denied(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    with pytest.raises(BoundaryDenied, match="undeclared effect"):
        d._apply("NETWORK", {})


def test_absolute_path_is_denied(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    with pytest.raises(BoundaryDenied, match="invalid path"):
        d._apply("WRITE", {"path": "/outside", "data": "x"})


def test_parent_escape_is_denied(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    with pytest.raises(BoundaryDenied, match="path escape"):
        d._apply("WRITE", {"path": "../outside", "data": "x"})


def test_nested_write_is_not_silently_included(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    with pytest.raises(BoundaryDenied, match="nested paths not enabled"):
        d._apply("WRITE", {"path": "sub/file", "data": "x"})
