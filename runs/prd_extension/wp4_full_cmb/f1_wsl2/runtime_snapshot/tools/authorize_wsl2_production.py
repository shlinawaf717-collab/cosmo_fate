#!/usr/bin/env python3
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
run = ROOT / "work/f1"
pre = ROOT / "work/preflight/PREFLIGHT_GO.json"
activation = run / "external_stop_activation.json"
if list(run.glob("c*/chain.*.txt")):
    print(json.dumps({"status": "EXISTING_SAMPLES_RESUME_ONLY"}))
    raise SystemExit(0)
preflight = json.loads(pre.read_text())
active = json.loads(activation.read_text())
if preflight.get("status") != "PASS" or active.get("status") != "ACTIVE_BEFORE_WSL2_PRODUCTION":
    raise RuntimeError("preflight/activation does not authorize production")
payload = {
    "schema_version": "wp4-f1-wsl2-production-start-v1",
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "production_authorized": True,
    "preflight_sha256": hashlib.sha256(pre.read_bytes()).hexdigest(),
    "activation_sha256": hashlib.sha256(activation.read_bytes()).hexdigest(),
    "mac_samples_included": False,
    "chain_seeds": [4511, 4512, 4513, 4514],
    "jobs": 4,
}
(run / "WSL2_PRODUCTION_STARTED.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(payload))
