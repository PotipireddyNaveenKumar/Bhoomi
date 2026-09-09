import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class RiskCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const RiskCard({Key? key, required this.data}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final score = data['overall_risk_score']?.toString() ?? '45';
    final level = data['overall_risk_level'] ?? 'MODERATE';
    final summary = data['summary'] ?? '';

    Color getLevelColor() {
      if (level == 'LOW') return AppColors.primaryGreen;
      if (level == 'MODERATE') return AppColors.warningOrange;
      return AppColors.errorRed;
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: getLevelColor().withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("🛡️ Farm Risk Assessment", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: getLevelColor().withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  "$level ($score/100)",
                  style: TextStyle(fontWeight: FontWeight.bold, color: getLevelColor(), fontSize: 13),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(summary, style: const TextStyle(fontSize: 14, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}
