import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class LeafDiagnosisCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const LeafDiagnosisCard({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    final crop = data['crop_identified'] ?? "Crop";
    final commonName = data['common_name'] ?? "Foliar Condition";
    final conf = (data['confidence_percentage'] ?? 0.0).toDouble();
    final uncertainty = data['uncertainty_level'] ?? "IN_DISTRIBUTION";
    final ipm = data['ipm_recommendation'] ?? "";
    final chem = data['chemical_treatment'] ?? "";
    final explanation = data['farmer_explanation'] ?? "";
    final warnings = data['safety_advisories'] as List<dynamic>? ?? [];
    final qualityMetrics = data['quality_gate_metrics'] as Map<String, dynamic>?;
    final requiresRetake = data['requires_retake'] == true;

    final isHealthy = commonName.toString().toLowerCase().contains("healthy");
    final isRejected = requiresRetake || uncertainty == "REJECTED" || conf < 55.0;

    Color badgeColor = AppColors.primaryGreen;
    if (isRejected) {
      badgeColor = Colors.red;
    } else if (!isHealthy) {
      badgeColor = Colors.orange;
    }

    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  isRejected
                      ? Icons.warning_amber_rounded
                      : (isHealthy ? Icons.check_circle_rounded : Icons.healing_rounded),
                  color: badgeColor,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            "$crop Diagnosis",
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: badgeColor.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              isRejected
                                  ? "FIELD INSPECTION REQUIRED"
                                  : (isHealthy ? "HEALTHY" : "DISEASE DETECTED"),
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: badgeColor,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        commonName,
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: badgeColor,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: badgeColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: badgeColor.withOpacity(0.3)),
                  ),
                  child: Text(
                    "${conf.toStringAsFixed(1)}% Conf",
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: badgeColor,
                    ),
                  ),
                )
              ],
            ),
            const SizedBox(height: 14),

            // Farmer Explanation
            Text(explanation, style: const TextStyle(fontSize: 14, height: 1.4)),

            // Quality Gate Metrics
            if (qualityMetrics != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    Text(
                      "Sharpness: ${qualityMetrics['sharpness_score']?.toString() ?? 'N/A'}",
                      style: const TextStyle(fontSize: 11, color: Colors.black54),
                    ),
                    Text(
                      "Brightness: ${qualityMetrics['brightness_mean']?.toString() ?? 'N/A'}",
                      style: const TextStyle(fontSize: 11, color: Colors.black54),
                    ),
                    Text(
                      "Uncertainty: $uncertainty",
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: isRejected ? Colors.red : Colors.black87,
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Recommendations if not healthy and not rejected
            if (!isHealthy && !isRejected) ...[
              const Divider(height: 24),
              if (ipm.isNotEmpty && ipm != "None") ...[
                const Text("🌱 Eco-Friendly IPM Action:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 4),
                Text(ipm, style: const TextStyle(fontSize: 13, height: 1.3)),
                const SizedBox(height: 10),
              ],
              if (chem.isNotEmpty && chem != "None") ...[
                const Text("🧪 Chemical Treatment Option:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 4),
                Text(chem, style: const TextStyle(fontSize: 13, height: 1.3)),
              ],
            ],

            // Safety Advisories / Warnings
            if (warnings.isNotEmpty) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.withOpacity(0.25)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.shield_outlined, color: Colors.red, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            "Safety Guardrail Advisory",
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.red),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            warnings.join("\n"),
                            style: const TextStyle(fontSize: 12, color: Colors.black87, height: 1.3),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              )
            ],

            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Icon(Icons.verified_user_outlined, size: 14, color: Colors.grey[500]),
                const SizedBox(width: 4),
                Text(
                  "Verified by BHOOMI Vision Pathology Engine",
                  style: TextStyle(fontSize: 11, color: Colors.grey[600], fontStyle: FontStyle.italic),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
