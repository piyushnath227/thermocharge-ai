from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.demo import build_demo_heatmap

pilot = json.loads((settings.data_dir / 'pilot.json').read_text(encoding='utf-8'))
heatmap = build_demo_heatmap(pilot)
out = settings.data_dir / 'demo_heatmap.json'
out.write_text(json.dumps(heatmap, indent=2), encoding='utf-8')
print(f'Wrote {out}')
print('WARNING: This is simulated development data, not FortyGuard output.')
