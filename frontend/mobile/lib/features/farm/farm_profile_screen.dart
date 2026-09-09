import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';
import '../../core/storage/secure_storage.dart';
import '../../routing/app_router.dart';

class FarmProfileScreen extends StatefulWidget {
  const FarmProfileScreen({Key? key}) : super(key: key);

  @override
  State<FarmProfileScreen> createState() => _FarmProfileScreenState();
}

class _FarmProfileScreenState extends State<FarmProfileScreen> {
  bool _isEditing = false;
  bool _isLoading = false;

  // Profile fields
  late TextEditingController _nameController;
  late TextEditingController _locationController;
  late TextEditingController _areaController;
  late TextEditingController _cropController;
  late TextEditingController _varietyController;
  late TextEditingController _soilController;
  late TextEditingController _irrigationController;
  late TextEditingController _sowingDateController;
  late TextEditingController _contactPrefController;

  // Original snapshot for CANCEL
  Map<String, String> _savedSnapshot = {};

  final List<Map<String, dynamic>> _lifecycleStages = const [
    {"stage": "Sowing & Nursery", "duration": "15 Days", "done": true},
    {"stage": "Transplantation", "duration": "10 Days", "done": true},
    {"stage": "Vegetative Growth", "duration": "35 Days", "done": true, "current": true},
    {"stage": "Flowering & Budding", "duration": "30 Days", "done": false},
    {"stage": "Fruit Formation", "duration": "40 Days", "done": false},
    {"stage": "Maturity & Harvest", "duration": "20 Days", "done": false},
  ];

  final List<Map<String, String>> _farmHistory = const [
    {"season": "Kharif 2023", "crop": "Chilli (Teja)", "yield": "28 Q/Acre", "realization": "₹12,400/Q", "net_profit": "₹1.85 Lakhs"},
    {"season": "Rabi 2022-23", "crop": "Black Gram (Intercrop)", "yield": "6 Q/Acre", "realization": "₹7,200/Q", "net_profit": "₹38,000"},
  ];

  final List<Map<String, String>> _recentDecisions = const [
    {"date": "Today", "decision": "Irrigation delayed by 48 hours", "source": "WeatherDecisionEngine", "status": "Active"},
    {"date": "2 days ago", "decision": "Foliar neem oil spray recommended", "source": "IPM SafetyEngine", "status": "Applied"},
    {"date": "Last week", "decision": "Vegetative fertilizer dose verified", "source": "Soil Health Card", "status": "Completed"},
  ];

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _locationController = TextEditingController();
    _areaController = TextEditingController();
    _cropController = TextEditingController();
    _varietyController = TextEditingController();
    _soilController = TextEditingController();
    _irrigationController = TextEditingController();
    _sowingDateController = TextEditingController();
    _contactPrefController = TextEditingController();
    _loadProfile();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _locationController.dispose();
    _areaController.dispose();
    _cropController.dispose();
    _varietyController.dispose();
    _soilController.dispose();
    _irrigationController.dispose();
    _sowingDateController.dispose();
    _contactPrefController.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    final profile = await LocalStorageService.getFarmProfile();
    setState(() {
      _savedSnapshot = Map<String, String>.from(profile);
      _nameController.text = profile["name"] ?? "";
      _locationController.text = profile["location"] ?? "";
      _areaController.text = profile["area"] ?? "";
      _cropController.text = profile["crop"] ?? "";
      _varietyController.text = profile["variety"] ?? "";
      _soilController.text = profile["soil"] ?? "";
      _irrigationController.text = profile["irrigation"] ?? "";
      _sowingDateController.text = profile["sowing_date"] ?? "";
      _contactPrefController.text = profile["contact_pref"] ?? "";
    });
  }

  void _cancelEditing() {
    setState(() {
      _nameController.text = _savedSnapshot["name"] ?? "";
      _locationController.text = _savedSnapshot["location"] ?? "";
      _areaController.text = _savedSnapshot["area"] ?? "";
      _cropController.text = _savedSnapshot["crop"] ?? "";
      _varietyController.text = _savedSnapshot["variety"] ?? "";
      _soilController.text = _savedSnapshot["soil"] ?? "";
      _irrigationController.text = _savedSnapshot["irrigation"] ?? "";
      _sowingDateController.text = _savedSnapshot["sowing_date"] ?? "";
      _contactPrefController.text = _savedSnapshot["contact_pref"] ?? "";
      _isEditing = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Changes discarded. Previous profile restored.")),
    );
  }

  Future<void> _saveProfile() async {
    final areaVal = double.tryParse(_areaController.text.trim());
    if (areaVal == null || areaVal <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please enter a valid farm area in acres."), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      // 1. Save to LocalStorageService
      await LocalStorageService.saveFarmProfile(
        name: _nameController.text.trim(),
        location: _locationController.text.trim(),
        area: _areaController.text.trim(),
        crop: _cropController.text.trim(),
        variety: _varietyController.text.trim(),
        soil: _soilController.text.trim(),
        irrigation: _irrigationController.text.trim(),
        sowingDate: _sowingDateController.text.trim(),
        contactPref: _contactPrefController.text.trim(),
      );

      // Update snapshot
      _savedSnapshot = {
        "name": _nameController.text.trim(),
        "location": _locationController.text.trim(),
        "area": _areaController.text.trim(),
        "crop": _cropController.text.trim(),
        "variety": _varietyController.text.trim(),
        "soil": _soilController.text.trim(),
        "irrigation": _irrigationController.text.trim(),
        "sowing_date": _sowingDateController.text.trim(),
        "contact_pref": _contactPrefController.text.trim(),
      };

      // 2. Persist to Backend API
      await ApiClient.post(ApiEndpoints.farms, {
        "farm_name": "Main Farm",
        "total_area_acres": areaVal,
        "soil_type": _soilController.text.trim(),
        "irrigation_source": _irrigationController.text.trim(),
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Farm Digital Twin successfully updated!"), backgroundColor: AppColors.primaryGreen),
      );
    } catch (_) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Profile updated locally."), backgroundColor: AppColors.primaryGreen),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isEditing = false;
        });
      }
    }
  }

  Future<void> _logout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Log Out of BHOOMI?"),
        content: const Text("You will be returned to the login screen."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("CANCEL")),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text("LOG OUT"),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await LocalStorageService.clear();
      if (mounted) {
        Navigator.pushNamedAndRemoveUntil(context, AppRouter.auth, (route) => false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: const Text("Farm Digital Twin & Profile"),
        backgroundColor: AppColors.primaryGreen,
        foregroundColor: Colors.white,
        actions: [
          if (!_isEditing)
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              tooltip: "Edit Profile",
              onPressed: () => setState(() => _isEditing = true),
            )
          else
            IconButton(
              icon: const Icon(Icons.close),
              tooltip: "Cancel",
              onPressed: _cancelEditing,
            ),
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            tooltip: "Log Out",
            onPressed: _logout,
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 860),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 1. Digital Twin Summary Card
                Container(
                  padding: const EdgeInsets.all(20.0),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20.0),
                    border: Border.all(
                      color: _isEditing ? AppColors.accentGold : AppColors.dividerColor,
                      width: _isEditing ? 2.0 : 1.0,
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4)),
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
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: AppColors.lightGreen,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: const Icon(Icons.agriculture_rounded, color: AppColors.primaryGreen, size: 28),
                              ),
                              const SizedBox(width: 12),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _nameController.text.isNotEmpty ? _nameController.text : "Farmer Profile",
                                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.textDark),
                                  ),
                                  Text(
                                    _locationController.text.isNotEmpty ? _locationController.text : "Location Not Configured",
                                    style: const TextStyle(fontSize: 13, color: AppColors.textMuted),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              color: AppColors.lightGreen,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppColors.primaryGreen.withOpacity(0.3)),
                            ),
                            child: Text(
                              "${_areaController.text} Acres",
                              style: const TextStyle(color: AppColors.primaryGreen, fontWeight: FontWeight.bold, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                      const Divider(height: 28),

                      if (!_isEditing) ...[
                        _buildDetailRow("Soil Type", _soilController.text),
                        _buildDetailRow("Irrigation Source", _irrigationController.text),
                        _buildDetailRow("Primary Crop", "${_cropController.text} (${_varietyController.text})"),
                        _buildDetailRow("Sowing Date", _sowingDateController.text),
                        _buildDetailRow("Current Stage", "Vegetative Growth (Day 38)"),
                        _buildDetailRow("Alerts Channel", _contactPrefController.text),
                      ] else ...[
                        // Edit Mode Fields
                        const Text(
                          "EDIT FARM PROFILE",
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.accentGold, letterSpacing: 0.8),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _nameController,
                          decoration: const InputDecoration(labelText: "Farmer Name", border: OutlineInputBorder()),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _locationController,
                          decoration: const InputDecoration(labelText: "Location", border: OutlineInputBorder()),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _areaController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: "Farm Area (Acres)", border: OutlineInputBorder()),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _cropController,
                                decoration: const InputDecoration(labelText: "Crop", border: OutlineInputBorder()),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _varietyController,
                                decoration: const InputDecoration(labelText: "Variety", border: OutlineInputBorder()),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _soilController,
                                decoration: const InputDecoration(labelText: "Soil Type", border: OutlineInputBorder()),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _irrigationController,
                                decoration: const InputDecoration(labelText: "Irrigation", border: OutlineInputBorder()),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _contactPrefController,
                          decoration: const InputDecoration(labelText: "Contact Preferences", border: OutlineInputBorder()),
                        ),
                        const SizedBox(height: 20),

                        // Action Buttons: Save & Cancel
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                style: OutlinedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(vertical: 14),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                                onPressed: _cancelEditing,
                                child: const Text("CANCEL DISCARD"),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppColors.primaryGreen,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(vertical: 14),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                                onPressed: _isLoading ? null : _saveProfile,
                                child: _isLoading
                                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                                    : const Text("SAVE PROFILE", style: TextStyle(fontWeight: FontWeight.bold)),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // 2. Crop Lifecycle Progression
                const Text("CROP LIFECYCLE PROGRESSION", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.textMuted)),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(16.0),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16.0),
                    border: Border.all(color: AppColors.dividerColor),
                  ),
                  child: Column(
                    children: _lifecycleStages.map((stg) {
                      final bool isDone = stg['done'] == true;
                      final bool isCurrent = stg['current'] == true;

                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6.0),
                        child: Row(
                          children: [
                            Icon(
                              isCurrent
                                  ? Icons.radio_button_checked
                                  : (isDone ? Icons.check_circle : Icons.radio_button_unchecked),
                              color: isCurrent
                                  ? AppColors.accentGold
                                  : (isDone ? AppColors.primaryGreen : AppColors.textMuted),
                              size: 22,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                stg['stage'],
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500,
                                  color: isCurrent ? AppColors.textDark : (isDone ? Colors.black87 : Colors.grey),
                                ),
                              ),
                            ),
                            Text(
                              stg['duration'],
                              style: TextStyle(fontSize: 12, color: isCurrent ? AppColors.accentGold : AppColors.textMuted, fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ),
                const SizedBox(height: 24),

                // 3. Historical Harvests & Realizations
                const Text("HARVEST & ECONOMIC HISTORY", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.textMuted)),
                const SizedBox(height: 12),
                ..._farmHistory.map((h) => Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppColors.dividerColor),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(h["season"]!, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                          Text(h["crop"]!, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text("Yield: ${h["yield"]}", style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                          Text("Net: ${h["net_profit"]}", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.primaryGreen)),
                        ],
                      ),
                    ],
                  ),
                )),
                const SizedBox(height: 20),

                // 4. Autonomous Decisions History
                const Text("RECENT AGRONOMIC DECISIONS", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.textMuted)),
                const SizedBox(height: 12),
                ..._recentDecisions.map((d) => Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.dividerColor),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle_outline, color: AppColors.primaryGreen, size: 20),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(d["decision"]!, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                            Text("${d["date"]!} • Grounding: ${d["source"]!}", style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                          ],
                        ),
                      ),
                    ],
                  ),
                )),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppColors.textDark)),
        ],
      ),
    );
  }
}
