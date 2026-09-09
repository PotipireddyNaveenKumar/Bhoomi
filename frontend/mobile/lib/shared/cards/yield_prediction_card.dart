import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class YieldPredictionCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const YieldPredictionCard({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    final crop = data['crop'] ?? "Crop";
    final acres = data['area_acres'] ?? 3.0;
    final yieldPerAcre = data['predicted_yield_quintals_per_acre'] ?? 0.0;
    final totalProd = data['total_estimated_production_quintals'] ?? 0.0;
    final ci = data['confidence_interval_quintals'] as List<dynamic>? ?? [0.0, 0.0];
    final assumptions = data['assumptions'] as List<dynamic>? ?? [];

    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.analytics_rounded, color: AppColors.primaryGreen, size: 28),
                const SizedBox(width: 8),
                Text(
                  "$crop Yield Prediction",
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.primaryGreen),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.primaryGreen.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    "$acres Acres",
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppColors.primaryGreen),
                  ),
                )
              ],
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _metricTile("Yield / Acre", "$yieldPerAcre Q"),
                _metricTile("Total Harvest", "$totalProd Q"),
                _metricTile("90% CI Range", "${ci[0]} - ${ci[1]} Q"),
              ],
            ),
            if (assumptions.isNotEmpty) ...[
              const Divider(height: 24),
              Text(
                "📌 ${assumptions.first}",
                style: TextStyle(fontSize: 12, color: Colors.grey[600], fontStyle: FontStyle.italic),
              )
            ]
          ],
        ),
      ),
    );
  }

  Widget _metricTile(String label, String value) {
    return Column(
      children: [
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
