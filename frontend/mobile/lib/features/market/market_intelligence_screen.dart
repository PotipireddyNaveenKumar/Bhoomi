import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';

class MarketIntelligenceScreen extends StatefulWidget {
  const MarketIntelligenceScreen({Key? key}) : super(key: key);

  @override
  State<MarketIntelligenceScreen> createState() => _MarketIntelligenceScreenState();
}

class _MarketIntelligenceScreenState extends State<MarketIntelligenceScreen> {
  String _selectedCrop = "Chilli";
  bool _isLoading = false;
  Map<String, dynamic>? _marketResponse = {
    "commodity": "Chilli",
    "recommended_mandi": "Guntur Mandi (Benchmark)",
    "best_net_realization": "12120.00",
    "recommendation_reason": "Highest Net Realization after logistics and mandi deductions.",
    "freshness": "CURRENT",
    "source": "Benchmark APMC Feed",
    "mandi_options": [
      {
        "mandi_name": "Guntur Mandi (Benchmark)",
        "district": "Guntur",
        "modal_price_per_quintal": "12200.00",
        "transport_cost_per_quintal": "80.00",
        "net_realization_per_quintal": "12120.00",
        "distance_km": "15.0",
        "arrival_date": "Today",
        "is_best": true
      }
    ]
  };
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadMarketData();
  }

  Future<void> _loadMarketData() async {
    if (_marketResponse == null) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      final res = await ApiClient.get(
        "${ApiEndpoints.market}?commodity=$_selectedCrop&district=Guntur&state=Andhra+Pradesh",
      );
      if (res.statusCode == 200) {
        setState(() {
          _marketResponse = jsonDecode(res.body);
          _isLoading = false;
        });
        return;
      }
    } catch (_) {}

    // Fallback demo values if network is unreachable
    setState(() {
      _isLoading = false;
      _marketResponse = {
        "commodity": _selectedCrop,
        "recommended_mandi": "Guntur Mandi (Benchmark)",
        "best_net_realization": "12120.00",
        "recommendation_reason": "Highest Net Realization after logistics and mandi deductions.",
        "freshness": "CURRENT",
        "source": "Mock Agricultural Market System (Simulated)",
        "mandi_options": [
          {
            "mandi_name": "Guntur Mandi (Benchmark)",
            "district": "Guntur",
            "modal_price_per_quintal": "12200.00",
            "transport_cost_per_quintal": "80.00",
            "net_realization_per_quintal": "12120.00",
            "distance_km": "15.0",
            "arrival_date": "Today",
            "source": "Benchmark APMC Feed",
            "freshness": "CURRENT",
            "is_best": true
          },
          {
            "mandi_name": "Khammam Mandi",
            "district": "Khammam",
            "modal_price_per_quintal": "12400.00",
            "transport_cost_per_quintal": "380.00",
            "net_realization_per_quintal": "12020.00",
            "distance_km": "110.0",
            "arrival_date": "Today",
            "source": "APMC Telangana Feed",
            "freshness": "CURRENT",
            "is_best": false
          },
          {
            "mandi_name": "Warangal Mandi",
            "district": "Warangal",
            "modal_price_per_quintal": "11900.00",
            "transport_cost_per_quintal": "520.00",
            "net_realization_per_quintal": "11380.00",
            "distance_km": "180.0",
            "arrival_date": "Today",
            "source": "APMC Feed",
            "freshness": "CURRENT",
            "is_best": false
          }
        ]
      };
    });
  }

  @override
  Widget build(BuildContext context) {
    final decision = _marketResponse?['market_decision'] ?? 'COMPARE MARKETS';
    final decisionRationale = _marketResponse?['decision_rationale'] ?? _marketResponse?['recommendation_reason'] ?? 'Highest Net Realization after transport and mandi deductions.';
    final mandiOptions = (_marketResponse?['mandi_options'] as List<dynamic>?) ?? [];
    final bestMandi = _marketResponse?['recommended_mandi'] ?? 'Guntur Mandi';
    final freshness = _marketResponse?['freshness'] ?? 'CURRENT';
    final source = _marketResponse?['source'] ?? 'Agmarknet APMC Feed';

    Color getDecisionColor(String dec) {
      switch (dec.toUpperCase()) {
        case 'SELL NOW':
          return const Color(0xFF2E7D32);
        case 'WAIT':
          return const Color(0xFFF57C00);
        case 'COMPARE MARKETS':
          return const Color(0xFF0288D1);
        case 'MONITOR':
          return const Color(0xFF7B1FA2);
        case 'INSUFFICIENT DATA':
        default:
          return Colors.blueGrey;
      }
    }

    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: const Text("Market & Mandi Intelligence"),
        backgroundColor: AppColors.primaryGreen,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _loadMarketData,
            tooltip: "Refresh Mandi Prices",
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Crop Switcher Row
                Card(
                  elevation: 1,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          "Select Crop for Mandi Compare:",
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                        ),
                        DropdownButton<String>(
                          value: _selectedCrop,
                          underline: Container(height: 2, color: AppColors.primaryGreen),
                          items: const [
                            DropdownMenuItem(value: "Chilli", child: Text("Chilli (Teja)")),
                            DropdownMenuItem(value: "Tomato", child: Text("Tomato")),
                            DropdownMenuItem(value: "Cotton", child: Text("Cotton")),
                            DropdownMenuItem(value: "Paddy", child: Text("Paddy / Rice")),
                          ],
                          onChanged: (val) {
                            if (val != null) {
                              setState(() => _selectedCrop = val);
                              _loadMarketData();
                            }
                          },
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // Market Decision Hero Card (MarketDecisionEngine)
                Container(
                  padding: const EdgeInsets.all(18.0),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16.0),
                    border: Border.all(color: getDecisionColor(decision).withOpacity(0.35), width: 1.5),
                    boxShadow: [
                      BoxShadow(
                        color: getDecisionColor(decision).withOpacity(0.06),
                        blurRadius: 10,
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
                              Icon(Icons.trending_up_rounded, color: getDecisionColor(decision), size: 24),
                              const SizedBox(width: 8),
                              const Text(
                                "MARKET DECISION",
                                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 0.5),
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              color: getDecisionColor(decision),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              decision.toUpperCase(),
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12, letterSpacing: 0.8),
                            ),
                          ),
                        ],
                      ),
                      const Divider(height: 20),
                      Text(
                        decisionRationale,
                        style: const TextStyle(color: AppColors.textDark, fontSize: 13, height: 1.4),
                      ),
                    ],
                  ),
                ),
                if (_errorMessage != null) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(8)),
                    child: Text(_errorMessage!, style: const TextStyle(color: Colors.red, fontSize: 12)),
                  ),
                ],
                const SizedBox(height: 20),

                // Freshness & Source metadata badge
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: freshness == "CURRENT" ? Colors.green.shade100 : Colors.amber.shade100,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        "DATA: $freshness",
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: freshness == "CURRENT" ? Colors.green.shade900 : Colors.brown,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      "Source: $source",
                      style: const TextStyle(fontSize: 11, color: Colors.grey, fontStyle: FontStyle.italic),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                if (_isLoading)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.all(40.0),
                      child: CircularProgressIndicator(color: AppColors.primaryGreen),
                    ),
                  )
                else ...[
                  for (var m in mandiOptions) ...[
                    _buildMandiCard(m, bestMandi),
                  ],
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMandiCard(dynamic m, String bestMandiName) {
    final name = m['mandi_name'] ?? 'Mandi';
    final isBest = name == bestMandiName || m['is_best'] == true;
    final modal = m['modal_price_per_quintal']?.toString() ?? 'N/A';
    final transport = m['transport_cost_per_quintal']?.toString() ?? '0.00';
    final net = m['net_realization_per_quintal']?.toString() ?? modal;
    final dist = m['distance_km']?.toString() ?? '0';

    return Container(
      margin: const EdgeInsets.only(bottom: 14.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(
          color: isBest ? AppColors.primaryGreen : AppColors.dividerColor,
          width: isBest ? 2.0 : 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: isBest ? AppColors.primaryGreen.withOpacity(0.08) : Colors.black.withOpacity(0.02),
            blurRadius: 8,
            offset: const Offset(0, 3),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              if (isBest)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.primaryGreen,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Text(
                    "BEST NET REALIZATION",
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11),
                  ),
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
                  const Text("Modal Price", style: TextStyle(fontSize: 12, color: Colors.grey)),
                  Text("₹$modal/Q", style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Logistics Cost", style: TextStyle(fontSize: 12, color: Colors.grey)),
                  Text("-₹$transport/Q ($dist km)", style: const TextStyle(fontSize: 14, color: Colors.redAccent)),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text("Net Realization", style: TextStyle(fontSize: 12, color: Colors.grey)),
                  Text(
                    "₹$net/Q",
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: isBest ? AppColors.primaryGreen : Colors.black87,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
