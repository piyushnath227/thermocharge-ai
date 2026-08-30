import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data_store import build_dashboard

snapshot = build_dashboard()
print('ThermoCharge smoke test ✅')
print('Data mode:', snapshot['data_mode'])
print('Chargers:', len(snapshot['chargers']))
print('Installed kW:', snapshot['summary']['installed_kw'])
print('Usable kW:', snapshot['summary']['usable_kw'])
print('Capacity at risk kW:', snapshot['summary']['capacity_at_risk_kw'])
print('Agent actions:', len(snapshot['actions']))
