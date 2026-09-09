import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class MarketCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const MarketCard({Key? key, required this.data}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final commodity = data['commodity'] ?? 'Chilli';
    final recommended = data['recommended_mandi'] ?? 'Guntur Mandi';
    final bestNet = data['best_net_realization']?.toString() ?? '12120.00';
    final reason = data['recommendation_reason'] ?? '';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: AppColors.accentGold.withOpacity(0.5)),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 10, offset: const Offset(0, 4)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                "💰 $commodity Mandi Realization",
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textDark),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.lightGreen,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text("Best Net Value", style: TextStyle(color: AppColors.primaryGreen, fontWeight: FontWeight.bold, fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            recommended,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.deepGreen),
          ),
          const SizedBox(height: 4),
          Text(
            "₹$bestNet / quintal (Net Realization)",
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: AppColors.primaryGreen),
          ),
          if (reason.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              reason,
              style: const TextStyle(fontSize: 13, color: AppColors.textMuted),
            ),
          ],
        ],
      ),
    );
  }
}
