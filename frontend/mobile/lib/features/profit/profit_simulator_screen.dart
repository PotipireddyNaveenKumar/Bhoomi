import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';
import '../../shared/cards/simulation_card.dart';

class ProfitSimulatorScreen extends StatefulWidget {
  const ProfitSimulatorScreen({Key? key}) : super(key: key);

  @override
  State<ProfitSimulatorScreen> createState() => _ProfitSimulatorScreenState();
}

class _ProfitSimulatorScreenState extends State<ProfitSimulatorScreen> {
  double _priceShift = -20.0;
  double _yieldShift = 0.0;
  double _costShift = 0.0;
  double _rainShift = -25.0;
  Map<String, dynamic>? _simResult;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _runSimulation();
  }

  Future<void> _runSimulation() async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiClient.post(ApiEndpoints.simulationRun, {
        "crop_name": "Chilli",
        "area_acres": 3.0,
        "baseline_yield_quintals_per_acre": 10.0,
        "baseline_market_price_per_quintal": 12000.0,
        "baseline_cultivation_cost": 70000.0,
        "price_change_percent": _priceShift,
        "yield_change_percent": _yieldShift,
        "cost_change_percent": _costShift,
        "rainfall_change_percent": _rainShift,
      });

      if (response.statusCode == 200) {
        setState(() {
          _simResult = jsonDecode(response.body);
        });
      }
    } catch (_) {
      // Offline fallback
      setState(() {
        _simResult = {
          "crop_name": "Chilli",
          "baseline": {"net_profit": "50000.00"},
          "simulated_scenario": {
            "net_profit": "26000.00",
            "profit_difference": "-24000.00",
            "percentage_profit_impact": "-48.0"
          },
          "risk_impact_explanation": "Price deflation of 20% reduces surplus margin by ₹24,000.",
          "recommended_hedging_actions": [
            "Consider phased selling across local and cold storage instead of immediate distress sale.",
            "Check transport arbitrage to Guntur benchmark mandi."
          ]
        };
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: const Text("What-If Farm Simulator"),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (_isLoading) const LinearProgressIndicator(color: AppColors.primaryGreen),
              const Text("Adjust scenarios to see exact financial impact on your farm:", style: TextStyle(color: AppColors.textMuted, fontSize: 14)),
              const SizedBox(height: 20),

              _buildSlider("Market Price Shift", "${_priceShift.toStringAsFixed(0)}%", _priceShift, -50.0, 50.0, (val) {
                setState(() => _priceShift = val);
                _runSimulation();
              }),
              _buildSlider("Rainfall Deficit / Gain", "${_rainShift.toStringAsFixed(0)}%", _rainShift, -50.0, 50.0, (val) {
                setState(() => _rainShift = val);
                _runSimulation();
              }),
              _buildSlider("Cultivation Cost Shift", "${_costShift.toStringAsFixed(0)}%", _costShift, -30.0, 50.0, (val) {
                setState(() => _costShift = val);
                _runSimulation();
              }),
              const SizedBox(height: 16),

              if (_simResult != null) ...[
                SimulationCard(data: _simResult!),
                const SizedBox(height: 16),
                const Text("RECOMMENDED HEDGING ACTIONS", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.textMuted)),
                const SizedBox(height: 8),
                for (var action in (_simResult!['recommended_hedging_actions'] as List<dynamic>? ?? [])) ...[
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4.0),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.check_circle, color: AppColors.primaryGreen, size: 18),
                        const SizedBox(width: 8),
                        Expanded(child: Text(action.toString(), style: const TextStyle(fontSize: 13, color: AppColors.textDark))),
                      ],
                    ),
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSlider(String title, String label, double value, double min, double max, ValueChanged<double> onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            Text(label, style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.primaryGreen, fontSize: 15)),
          ],
        ),
        Slider(
          value: value,
          min: min,
          max: max,
          divisions: 20,
          activeColor: AppColors.primaryGreen,
          onChanged: onChanged,
        ),
      ],
    );
  }
}
