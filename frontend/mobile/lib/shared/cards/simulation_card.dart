import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class SimulationCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const SimulationCard({Key? key, required this.data}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final crop = data['crop_name'] ?? 'Chilli';
    final baseline = data['baseline'] as Map<String, dynamic>? ?? {};
    final sim = data['simulated_scenario'] as Map<String, dynamic>? ?? {};
    final baseProfit = baseline['net_profit']?.toString() ?? '50000.00';
    final simProfit = sim['net_profit']?.toString() ?? '26000.00';
    final diff = sim['profit_difference']?.toString() ?? '-24000.00';
    final impactPct = sim['percentage_profit_impact']?.toString() ?? '-48.0';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: AppColors.warningOrange.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("⚡ What-If Simulator: $crop", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.warningOrange.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text("$impactPct%", style: const TextStyle(color: AppColors.warningOrange, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Baseline Profit", style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  Text("₹$baseProfit", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                ],
              ),
              const Icon(Icons.arrow_forward, color: AppColors.textMuted),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text("Simulated Profit", style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  Text("₹$simProfit", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.warningOrange)),
                ],
              ),
            ],
          ),
          const Divider(height: 20),
          Text(
            "Difference: ₹$diff net surplus shift",
            style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.textDark, fontSize: 14),
          ),
        ],
      ),
    );
  }
}
