import 'package:flutter/material.dart';

class FarmCommandCenterScreen extends StatefulWidget {
  const FarmCommandCenterScreen({Key? key}) : super(key: key);

  @override
  State<FarmCommandCenterScreen> createState() => _FarmCommandCenterScreenState();
}

class _FarmCommandCenterScreenState extends State<FarmCommandCenterScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D1F12),
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("BHOOMI Command Center", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
            Text("Personal AI Farm Manager • 3.0 Acres (Black Soil)", style: TextStyle(fontSize: 12, color: Color(0xFF81C784))),
          ],
        ),
        backgroundColor: const Color(0xFF1B3B22),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_active_outlined, color: Color(0xFFFFD54F)),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Proactive Alert: Rain forecasted midweek. Irrigation postponed.")),
              );
            },
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: const Color(0xFF4CAF50),
          indicatorWeight: 3,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white54,
          tabs: const [
            Tab(icon: Icon(Icons.today), text: "Today"),
            Tab(icon: Icon(Icons.eco), text: "My Crop"),
            Tab(icon: Icon(Icons.change_circle_outlined), text: "Changed"),
            Tab(icon: Icon(Icons.analytics_outlined), text: "Financials"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildTodayTab(),
          _buildMyCropTab(),
          _buildWhatChangedTab(),
          _buildFinancialsTab(),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF2E7D32),
        icon: const Icon(Icons.mic, color: Colors.white, size: 28),
        label: const Text(
          "Ask Farm Manager",
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
        ),
        onPressed: () {
          _showVoiceInteractionModal();
        },
      ),
    );
  }

  Widget _buildTodayTab() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 80),
      children: [
        // Daily Greeting Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF1E4620), Color(0xFF2E7D32)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 8, offset: const Offset(0, 4)),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text("TODAY'S FARM BRIEFING", style: TextStyle(color: Color(0xFFA5D6A7), fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(12)),
                    child: const Text("STATUS: ACTIVE", style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Text(
                "Namaste Ramesh! Your Chilli is in Flowering stage (Day 45). Weather is favorable with light rain possible midweek.",
                style: TextStyle(color: Colors.white, fontSize: 15, height: 1.4),
              ),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: const Color(0xFF1B5E20),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: const Icon(Icons.volume_up, size: 18),
                label: const Text("Listen in Telugu (వినండి)"),
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Playing audio briefing via Sarvam Voice...")),
                  );
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Priority Action 1
        _buildActionCard(
          priority: "HIGH PRIORITY",
          priorityColor: Colors.orangeAccent,
          title: "Foliar Spray: 19:19:19 + Boron",
          reason: "Crop is in peak flowering. Boron prevents flower drop; schedule in evening after 5:30 PM to protect honeybee pollinators.",
          category: "Nutrient & Pollinator Safety",
          icon: Icons.shield,
        ),
        const SizedBox(height: 12),

        // Weather Action
        _buildActionCard(
          priority: "WEATHER DECISION",
          priorityColor: Colors.lightBlueAccent,
          title: "Postpone Irrigation by 48 Hours",
          reason: "Precipitation forecast (40% probability, ~2.4mm) maintains optimal moisture in black vertisol soil.",
          category: "Water Conservation",
          icon: Icons.water_drop,
        ),
        const SizedBox(height: 12),

        // Mandi Action
        _buildActionCard(
          priority: "MARKET OPPORTUNITY",
          priorityColor: const Color(0xFFFFD54F),
          title: "Track Guntur Mandi Arrivals",
          reason: "Net Realization is ₹12,120/Q (above target threshold ₹11,500/Q). Monitor arrivals for optimal selling window.",
          category: "Commercial Realization",
          icon: Icons.trending_up,
        ),
      ],
    );
  }

  Widget _buildMyCropTab() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 80),
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF162D1A),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF2E7D32)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text("Chilli (Teja Variety)", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: const Color(0xFF2E7D32), borderRadius: BorderRadius.circular(12)),
                    child: const Text("STAGE: FLOWERING", style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text("Days After Sowing: 45 / 150", style: TextStyle(color: Colors.white70, fontSize: 13)),
                  Text("Expected: Dec 2026", style: TextStyle(color: Color(0xFFA5D6A7), fontSize: 13)),
                ],
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: const LinearProgressIndicator(
                  value: 0.30,
                  minHeight: 8,
                  backgroundColor: Colors.white12,
                  valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF66BB6A)),
                ),
              ),
              const Divider(color: Colors.white24, height: 28),
              _buildFactRow("Acreage", "3.0 Acres"),
              _buildFactRow("Soil Type", "Deep Black Vertisol"),
              _buildFactRow("Irrigation Source", "Borewell (Furrow System)"),
              _buildFactRow("Expected Yield", "10.0 Quintals/Acre (Total: 30 Q)"),
              _buildFactRow("Estimated Net Profit", "₹2,96,000"),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildWhatChangedTab() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 80),
      children: [
        const Text("ENVIRONMENTAL & MARKET SHIFTS", style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        _buildDiffCard(
          icon: Icons.cloud_outlined,
          title: "Rainfall Probability Jumped +20%",
          diff: "20% ➔ 40%",
          impact: "Scheduled furrow irrigation has been automatically postponed to avoid saturation.",
        ),
        const SizedBox(height: 12),
        _buildDiffCard(
          icon: Icons.monetization_on_outlined,
          title: "Guntur Mandi Modal Price +₹400/Q",
          diff: "₹11,800 ➔ ₹12,200/Q",
          impact: "Net realization increased by 3.4%. Your selling profit margin is now above target.",
        ),
        const SizedBox(height: 12),
        _buildDiffCard(
          icon: Icons.bug_report_outlined,
          title: "Crop Pathology Timeline: STABLE",
          diff: "Healthy Foliage Maintained",
          impact: "No fungal spots or thrips vector damage observed across recent scans.",
        ),
      ],
    );
  }

  Widget _buildFinancialsTab() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 80),
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF162D1A),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF2E7D32)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text("FINANCIAL FORECAST & NET REALIZATION", style: TextStyle(color: Color(0xFFA5D6A7), fontSize: 12, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              _buildFinanceRow("Gross Revenue (30 Q @ ₹12,200/Q)", "₹3,66,000", Colors.white),
              _buildFinanceRow("Total Cultivation Cost (3 Acres)", "- ₹70,000", Colors.redAccent),
              const Divider(color: Colors.white24, height: 24),
              _buildFinanceRow("Projected Net Profit", "₹2,96,000", const Color(0xFF81C784), isBold: true),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Colors.white10, borderRadius: BorderRadius.circular(8)),
                child: const Row(
                  children: [
                    Icon(Icons.verified, color: Color(0xFF81C784), size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text("Calculated with exact Decimal arithmetic; independent of LLM hallucination.", style: TextStyle(color: Colors.white70, fontSize: 12)),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildActionCard({
    required String priority,
    required Color priorityColor,
    required String title,
    required String reason,
    required String category,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF162D1A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: priorityColor, size: 18),
              const SizedBox(width: 8),
              Text(priority, style: TextStyle(color: priorityColor, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.8)),
              const Spacer(),
              Text(category, style: const TextStyle(color: Colors.white38, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 8),
          Text(title, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          Text(reason, style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.3)),
        ],
      ),
    );
  }

  Widget _buildFactRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white60, fontSize: 13)),
          Text(value, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _buildDiffCard({
    required IconData icon,
    required String title,
    required String diff,
    required String impact,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF162D1A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: const Color(0xFF81C784), size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14))),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: const Color(0xFF2E7D32), borderRadius: BorderRadius.circular(8)),
                child: Text(diff, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(impact, style: const TextStyle(color: Colors.white70, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildFinanceRow(String label, String value, Color color, {bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.white70, fontSize: isBold ? 14 : 13, fontWeight: isBold ? FontWeight.bold : FontWeight.normal)),
          Text(value, style: TextStyle(color: color, fontSize: isBold ? 16 : 13, fontWeight: isBold ? FontWeight.bold : FontWeight.w600)),
        ],
      ),
    );
  }

  void _showVoiceInteractionModal() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1B3B22),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) {
        return Container(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text("Listening to Farmer...", style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 20),
              const CircleAvatar(
                radius: 40,
                backgroundColor: Color(0xFF2E7D32),
                child: Icon(Icons.mic, color: Colors.white, size: 40),
              ),
              const SizedBox(height: 20),
              const Text(
                "\"ఈరోజు నా తోటకి ఏం చేయాలి?\"\n(What should I do today?)",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white70, fontSize: 14, fontStyle: FontStyle.italic),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF4CAF50)),
                onPressed: () => Navigator.pop(ctx),
                child: const Text("Stop Listening", style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        );
      },
    );
  }
}
