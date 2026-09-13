import pytest
from dar.boundary import BoundaryDenied, PrivilegedDispatcher


def test_undeclared_effect_is_denied(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    with pytest.raises(BoundaryDenied, match="undeclared effect"):
        d.execute("NETWORK", {})


def test_absolute_path_is_denied(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    with pytest.raises(BoundaryDenied, match="invalid path"):
        d.execute("WRITE", {"path": "/outside", "data": "x"})


def test_parent_escape_is_denied(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    with pytest.raises(BoundaryDenied, match="path escape"):
        d.execute("WRITE", {"path": "../outside", "data": "x"})


def test_nested_write_is_not_silently_included(tmp_path):
    d = PrivilegedDispatcher(tmp_path / "root")
    with pytest.raises(BoundaryDenied, match="nested paths not enabled"):
        d.execute("WRITE", {"path": "sub/file", "data": "x"})
