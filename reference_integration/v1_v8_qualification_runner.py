#!/usr/bin/env python3
"""Runtime wrapper for V1-V8 qualification.

The authoritative state is owned by darauthority. V8 needs a rollback snapshot,
so the snapshot copy is deliberately performed as darauthority rather than by
the unprivileged runner. The attacker-side restore attempt remains unchanged.
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

import v1_v8_qualification as qualification

_original_copy2 = shutil.copy2

def _copy2_with_authority_snapshot(src, dst, *args, **kwargs):
    src_path = Path(src)
    dst_path = Path(dst)
    if src_path.name == "authority_state.json" and dst_path.name == "authority_state.snapshot":
        subprocess.run(
            ["sudo", "-u", "darauthority", "--", "cp", str(src_path), str(dst_path)],
            check=True,
        )
        subprocess.run(["sudo", "chmod", "600", str(dst_path)], check=True)
        return str(dst_path)
    return _original_copy2(src, dst, *args, **kwargs)

qualification.shutil.copy2 = _copy2_with_authority_snapshot

if __name__ == "__main__":
    raise SystemExit(qualification.main())
