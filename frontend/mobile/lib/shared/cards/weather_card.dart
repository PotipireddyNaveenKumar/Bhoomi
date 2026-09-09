import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class WeatherCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const WeatherCard({Key? key, required this.data}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) {
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 8.0),
        padding: const EdgeInsets.all(16.0),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16.0),
          border: Border.all(color: AppColors.dividerColor),
        ),
        child: const Row(
          children: [
            Icon(Icons.cloud_off, color: AppColors.textMuted),
            SizedBox(width: 8),
            Text("Weather data unavailable.", style: TextStyle(color: AppColors.textMuted)),
          ],
        ),
      );
    }

    final current = data['current'] as Map<String, dynamic>? ?? {};
    final location = data['location'] ?? 'Guntur';
    final temp = current['temperature_c']?.toString() ?? '31.5';
    final rainProb = current['rain_probability_percent']?.toString() ?? '40';
    final condition = current['weather_condition'] ?? 'Partly Cloudy';
    final advisory = current['advisory'] ?? 'Optimal agricultural conditions.';
    final humidity = current['humidity_percent']?.toString() ?? '68';
    final rainfall = current['rainfall_mm']?.toString() ?? '0.0';
    final freshness = data['freshness'] ?? current['freshness'] ?? 'CURRENT';
    final source = data['source'] ?? current['source'] ?? 'OpenWeatherMap / Agromet Live';

    Color getFreshnessColor() {
      switch (freshness.toString().toUpperCase()) {
        case 'CURRENT':
          return const Color(0xFF2E7D32);
        case 'CACHED':
          return const Color(0xFFF9A825);
        default:
          return const Color(0xFF757575);
      }
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFE1F5FE), Color(0xFFB3E5FC)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: AppColors.skyBlue.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.cloud, color: AppColors.skyBlue, size: 28),
                  const SizedBox(width: 8),
                  Text(
                    location,
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark),
                  ),
                ],
              ),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: getFreshnessColor().withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: getFreshnessColor().withOpacity(0.4)),
                    ),
                    child: Text(
                      freshness.toString().toUpperCase(),
                      style: TextStyle(fontWeight: FontWeight.bold, color: getFreshnessColor(), fontSize: 11),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.skyBlue.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      "$rainProb% Rain Chance",
                      style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.skyBlue, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                "$temp°C",
                style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: AppColors.textDark),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  condition,
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textDark),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              _buildMetric(Icons.water_drop_outlined, "Humidity", "$humidity%"),
              const SizedBox(width: 18),
              _buildMetric(Icons.grain_outlined, "Rainfall", "${rainfall}mm"),
              const Spacer(),
              Text(
                source,
                style: const TextStyle(fontSize: 11, color: AppColors.textMuted, fontStyle: FontStyle.italic),
              ),
            ],
          ),
          const Divider(height: 20),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline, color: AppColors.skyBlue, size: 18),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  advisory,
                  style: const TextStyle(fontSize: 13, color: AppColors.textDark, fontWeight: FontWeight.w500),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetric(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, size: 14, color: AppColors.skyBlue),
        const SizedBox(width: 4),
        Text(
          "$label: ",
          style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
        ),
        Text(
          value,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.textDark),
        ),
      ],
    );
  }
}
