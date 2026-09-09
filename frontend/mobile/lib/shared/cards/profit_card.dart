import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class ProfitCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const ProfitCard({Key? key, required this.data}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final crop = data['crop_name'] ?? 'Chilli';
    final area = data['area_acres']?.toString() ?? '3.0';
    final revenue = data['gross_revenue']?.toString() ?? '120000.00';
    final cost = data['cultivation_cost_total']?.toString() ?? '70000.00';
    final netProfit = data['net_profit']?.toString() ?? '50000.00';
    final roi = data['return_on_investment_percent']?.toString() ?? '71.4';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: AppColors.primaryGreen.withOpacity(0.3)),
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
                "📊 Financial Plan: $crop ($area acres)",
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textDark),
              ),
              Text(
                "ROI: $roi%",
                style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.primaryGreen, fontSize: 14),
              ),
            ],
          ),
          const Divider(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Gross Revenue", style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  const SizedBox(height: 2),
                  Text("₹$revenue", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.textDark)),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Total Cost", style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  const SizedBox(height: 2),
                  Text("₹$cost", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.errorRed)),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Net Profit", style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  const SizedBox(height: 2),
                  Text("₹$netProfit", style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: AppColors.primaryGreen)),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
