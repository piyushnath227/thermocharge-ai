from app.data_store import build_dashboard


def test_dashboard_builds():
    d = build_dashboard()
    assert d['project'] == 'ThermoCharge AI'
    assert len(d['chargers']) == 8
    assert d['summary']['installed_kw'] == 1800.0
    assert d['actions']
