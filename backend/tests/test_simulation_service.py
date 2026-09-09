import pytest
from decimal import Decimal
from app.services.simulation.simulation_service import SimulationService
from app.schemas.simulation import SimulationRequest

def test_what_if_simulation_price_drop_20():
    """
    Validates -20% price drop scenario:
    Baseline: 10 quintals * 12,000 = 1,20,000 revenue - 70,000 cost = 50,000 profit
    Price -20% -> 9,600/quintal
    Simulated: 10 quintals * 9,600 = 96,000 revenue - 70,000 cost = 26,000 profit
    Difference: -24,000 (-48% profit impact)
    """
    req = SimulationRequest(
        crop_name="Chilli",
        area_acres=Decimal("1.0"),
        baseline_yield_quintals_per_acre=Decimal("10.0"),
        baseline_market_price_per_quintal=Decimal("12000.00"),
        baseline_cultivation_cost=Decimal("70000.00"),
        price_change_percent=Decimal("-20.0"),
        yield_change_percent=Decimal("0.0"),
        cost_change_percent=Decimal("0.0"),
        rainfall_change_percent=Decimal("0.0"),
    )
    res = SimulationService.run_simulation(req)

    assert res.baseline.net_profit == Decimal("50000.00")
    assert res.simulated_scenario.price_per_quintal == Decimal("9600.00")
    assert res.simulated_scenario.gross_revenue == Decimal("96000.00")
    assert res.simulated_scenario.net_profit == Decimal("26000.00")
    assert res.simulated_scenario.profit_difference == Decimal("-24000.00")
    assert res.simulated_scenario.percentage_profit_impact == Decimal("-48.00")

def test_what_if_simulation_cost_and_yield_surge():
    """
    Validates +10% cost increase and +15% yield gain.
    """
    req = SimulationRequest(
        crop_name="Cotton",
        area_acres=Decimal("2.0"),
        baseline_yield_quintals_per_acre=Decimal("8.0"),
        baseline_market_price_per_quintal=Decimal("7000.00"),
        baseline_cultivation_cost=Decimal("60000.00"),
        price_change_percent=Decimal("0.0"),
        yield_change_percent=Decimal("15.0"),
        cost_change_percent=Decimal("10.0"),
        rainfall_change_percent=Decimal("0.0"),
    )
    res = SimulationService.run_simulation(req)

    # 2 acres * 8 q = 16 quintals baseline; 16 * 7000 = 1,12,000; - 60000 = 52,000 baseline profit
    assert res.baseline.net_profit == Decimal("52000.00")
    # Yield +15% -> 18.40 quintals; Cost +10% -> 66,000; Revenue -> 18.4 * 7000 = 128,800; Profit -> 62,800
    assert res.simulated_scenario.total_yield_quintals == Decimal("18.40")
    assert res.simulated_scenario.cultivation_cost == Decimal("66000.00")
    assert res.simulated_scenario.gross_revenue == Decimal("128800.00")
    assert res.simulated_scenario.net_profit == Decimal("62800.00")
