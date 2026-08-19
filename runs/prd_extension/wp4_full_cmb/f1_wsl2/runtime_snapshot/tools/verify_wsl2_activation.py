#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


p = argparse.ArgumentParser()
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
activation = json.loads((ROOT / "work/f1/external_stop_activation.json").read_text())
failures = []
for group in ("hashes", "runtime_hashes", "preflight_hashes"):
    for name, record in activation[group].items():
        path = ROOT / record["path"]
        if not path.is_file() or sha(path) != record["sha256"]:
            failures.append(f"{group}.{name}")
payload = {
    "schema_version": "wp4-f1-wsl2-activation-verification-v1",
    "status": "PASS" if not failures else "FAIL",
    "failures": failures,
    "mac_samples_included": activation.get("mac_samples_included"),
}
a.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(json.dumps(payload))
raise SystemExit(0 if not failures and payload["mac_samples_included"] is False else 1)
