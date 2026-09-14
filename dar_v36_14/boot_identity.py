from __future__ import annotations

import os
import uuid

BOOT_ID = os.environ.get("DAR_BOOT_ID") or str(uuid.uuid4())
