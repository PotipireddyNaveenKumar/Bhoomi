import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class MarketCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const MarketCard({Key? key, required this.data}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final commodity = data['commodity'] ?? 'Crop';
    final freshness = data['freshness'] ?? 'CURRENT';
    final isUnavailable = freshness == 'UNAVAILABLE' || data['best_net_realization'] == null;
    final isDemo = data['is_synthetic'] == true || freshness == 'DEMO';
    final recommended = data['recommended_mandi'] ?? (isUnavailable ? 'Regional Mandi' : 'APMC Mandi');
    final rawNet = data['best_net_realization'];
    final bestNet = rawNet != null ? rawNet.toString() : null;
    final reason = data['recommendation_reason'] ?? (isUnavailable ? 'Official mandi arrivals and spot quotes not reported for today.' : '');

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: isUnavailable ? Colors.amber.shade300 : AppColors.accentGold.withOpacity(0.5)),
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
                  color: isUnavailable ? Colors.amber.shade50 : (isDemo ? Colors.blue.shade50 : AppColors.lightGreen),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  isUnavailable ? "Data Unavailable" : (isDemo ? "Demo Data" : "Best Net Value"),
                  style: TextStyle(
                    color: isUnavailable ? Colors.amber.shade900 : (isDemo ? Colors.blue.shade800 : AppColors.primaryGreen),
                    fontWeight: FontWeight.bold,
                    fontSize: 12
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            recommended,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: isUnavailable ? Colors.grey.shade700 : AppColors.deepGreen
            ),
          ),
          const SizedBox(height: 4),
          Text(
            isUnavailable ? "Live Rates Unavailable" : "₹$bestNet / quintal (Net Realization)",
            style: TextStyle(
              fontSize: isUnavailable ? 16 : 20,
              fontWeight: FontWeight.w900,
              color: isUnavailable ? Colors.grey.shade600 : AppColors.primaryGreen
            ),
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
