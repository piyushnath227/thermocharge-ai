from app.models import Charger
from app.services.thermal import DEFAULT_PROFILE, evaluate_charger


def charger():
    return Charger(
        id='X', site_id='S', site_name='Test', charger_name='Unit', network='Test',
        address='Test', latitude=33.0, longitude=-112.0, rated_kw=350,
        connector='CCS', data_source='test', source_url='https://example.com',
        modeled_demand_fraction=0.5,
    )


def test_reference_curve():
    assert DEFAULT_PROFILE.capacity_factor(25) == 1.0
    assert round(DEFAULT_PROFILE.capacity_factor(35), 2) == 0.80
    assert DEFAULT_PROFILE.capacity_factor(50) == 0.50


def test_capacity_result():
    r = evaluate_charger(charger(), 35)
    assert r.usable_kw == 280.0
    assert r.capacity_at_risk_kw == 70.0
    assert r.risk_level == 'MODERATE'
