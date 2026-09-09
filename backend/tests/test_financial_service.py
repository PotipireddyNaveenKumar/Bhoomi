import pytest
from decimal import Decimal
from app.services.finance.profit_service import FinancialService
from app.schemas.finance import ProfitCalculationRequest

def test_profit_calculation_exact_specification():
    """
    Validates exact prompt specification:
    10 quintals * 12,000 = 1,20,000 revenue
    1,20,000 - 70,000 = 50,000 net profit
    """
    req = ProfitCalculationRequest(
        crop_name="Chilli",
        area_acres=Decimal("1.0"),
        expected_yield_quintals_per_acre=Decimal("10.0"),
        expected_market_price_per_quintal=Decimal("12000.00"),
        cultivation_cost_total=Decimal("70000.00")
    )
    res = FinancialService.calculate_profit(req)
    
    assert res.total_production_quintals == Decimal("10.00")
    assert res.gross_revenue == Decimal("120000.00")
    assert res.net_profit == Decimal("50000.00")
    assert res.profit_per_acre == Decimal("50000.00")
    assert res.return_on_investment_percent == Decimal("71.43")

def test_profit_calculation_3_acres():
    """
    Validates 3 acres calculation:
    3 acres * 10 q/acre = 30 quintals
    30 quintals * 12,000 = 3,60,000 revenue
    3,60,000 - 1,50,000 = 2,10,000 profit
    """
    req = ProfitCalculationRequest(
        crop_name="Chilli",
        area_acres=Decimal("3.0"),
        expected_yield_quintals_per_acre=Decimal("10.0"),
        expected_market_price_per_quintal=Decimal("12000.00"),
        cultivation_cost_total=Decimal("150000.00")
    )
    res = FinancialService.calculate_profit(req)

    assert res.total_production_quintals == Decimal("30.00")
    assert res.gross_revenue == Decimal("360000.00")
    assert res.net_profit == Decimal("210000.00")
    assert res.profit_per_acre == Decimal("70000.00")

def test_profit_loss_scenario():
    """
    Tests loss scenario where costs exceed revenue.
    """
    req = ProfitCalculationRequest(
        crop_name="Chilli",
        area_acres=Decimal("2.0"),
        expected_yield_quintals_per_acre=Decimal("4.0"),
        expected_market_price_per_quintal=Decimal("8000.00"),
        cultivation_cost_total=Decimal("90000.00")
    )
    res = FinancialService.calculate_profit(req)

    assert res.total_production_quintals == Decimal("8.00")
    assert res.gross_revenue == Decimal("64000.00")
    assert res.net_profit == Decimal("-26000.00")
    assert res.profit_per_acre == Decimal("-13000.00")
