import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class CropRecommendationCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const CropRecommendationCard({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    final crops = data['recommended_crops'] as List<dynamic>? ?? [];
    final advisory = data['advisory'] as String? ?? "Recommended crops based on your soil test and rainfall.";
    final warnings = data['warnings'] as List<dynamic>? ?? [];

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
                const Icon(Icons.eco_rounded, color: AppColors.primaryGreen, size: 28),
                const SizedBox(width: 8),
                const Text(
                  "Crop Recommendation",
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.primaryGreen),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.accentGold.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text("ML Verified", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                )
              ],
            ),
            const SizedBox(height: 12),
            Text(advisory, style: const TextStyle(fontSize: 14, height: 1.4)),
            const Divider(height: 24),
            ...crops.map((c) {
              final cropMap = c as Map<String, dynamic>;
              final pct = cropMap['percentage'] ?? 0.0;
              return Padding(
                padding: const EdgeInsets.only(bottom: 12.0),
                child: Row(
                  children: [
                    CircleAvatar(
                      backgroundColor: AppColors.primaryGreen.withOpacity(0.1),
                      child: Text(
                        cropMap['crop']?.toString().substring(0, 1) ?? "C",
                        style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.primaryGreen),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(cropMap['crop'] ?? "", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                          Text("Suitability: ${cropMap['suitability'] ?? 'Optimal'}", style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                        ],
                      ),
                    ),
                    Text(
                      "$pct%",
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.primaryGreen),
                    )
                  ],
                ),
              );
            }).toList(),
            if (warnings.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        warnings.first.toString(),
                        style: const TextStyle(fontSize: 12, color: Colors.deepOrange),
                      ),
                    ),
                  ],
                ),
              )
            ]
          ],
        ),
      ),
    );
  }
}
