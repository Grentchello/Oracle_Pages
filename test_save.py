import sys
sys.path.insert(0, "/opt/data/hermes_work/bot")
import json
from pathlib import Path

state_path = Path("/opt/data/hermes_work/wiki/trading/state.json")
s = json.loads(state_path.read_text())
print(f"Before: positions={len(s['positions'])}, trades={len(s.get('trades', []))}")

# Mutate
s["trades"].append({"mint": "test", "symbol": "DEBUG"})
if s["positions"]:
    del s["positions"][list(s["positions"].keys())[0]]
print(f"Modified: positions={len(s['positions'])}, trades={len(s['trades'])}")

# Save
state_path.write_text(json.dumps(s, indent=2, ensure_ascii=False))
print("Saved")

# Reload
s2 = json.loads(state_path.read_text())
print(f"After: positions={len(s2['positions'])}, trades={len(s2['trades'])}")