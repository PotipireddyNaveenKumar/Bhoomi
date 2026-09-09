import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';
import '../../core/storage/secure_storage.dart';
import '../../localization/app_localizations.dart';
import '../../shared/widgets/voice_orb.dart';
import '../../shared/cards/weather_card.dart';
import '../../shared/cards/market_card.dart';
import '../../shared/cards/task_card.dart';
import '../../routing/app_router.dart';

class HomeScreen extends StatefulWidget {
  final Function(Locale)? onLanguageChanged;
  const HomeScreen({Key? key, this.onLanguageChanged}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  VoiceState _voiceState = VoiceState.idle;
  String _farmerName = "";
  String _farmerLocation = "";
  String _currentLanguage = "en";
  Map<String, dynamic>? _weatherData;
  Map<String, dynamic>? _marketData;
  List<Map<String, dynamic>> _todayTasks = [];
  bool _isLoading = true;

  final Map<String, String> _languageNames = {
    "en": "English",
    "te": "తెలుగు",
    "hi": "हिन्दी",
    "ta": "தமிழ்",
    "kn": "ಕನ್ನಡ",
    "ml": "മലയാളം",
  };

  @override
  void initState() {
    super.initState();
    _loadLanguage();
    _loadDashboardData();
  }

  Future<void> _loadLanguage() async {
    final lang = await LocalStorageService.getLanguage();
    setState(() {
      _currentLanguage = lang;
    });
  }

  Future<void> _changeLanguage(String newLang) async {
    await LocalStorageService.setLanguage(newLang);
    setState(() {
      _currentLanguage = newLang;
    });
    widget.onLanguageChanged?.call(Locale(newLang));
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);
    final profile = await LocalStorageService.getFarmProfile();
    final name = profile['name']?.isNotEmpty == true ? profile['name']! : (await LocalStorageService.getUserName() ?? "");
    if (name.isNotEmpty) {
      _farmerName = name;
    }
    _farmerLocation = profile['location'] ?? "";

    final location = profile['location']?.split(',').first.trim().isNotEmpty == true
        ? profile['location']!.split(',').first.trim()
        : "Guntur";
    final state = profile['location']?.contains(',') == true
        ? profile['location']!.split(',').last.trim()
        : "Andhra Pradesh";
    final crop = profile['crop']?.isNotEmpty == true ? profile['crop']! : "Chilli";

    try {
      // 1. Fetch Live Weather for farmer's location
      final weatherRes = await ApiClient.get("${ApiEndpoints.weather}?location=${Uri.encodeComponent(location)}");
      if (weatherRes.statusCode == 200) {
        _weatherData = jsonDecode(weatherRes.body);
      }

      // 2. Fetch Market Prices for farmer's crop and location
      final marketRes = await ApiClient.get("${ApiEndpoints.market}?commodity=${Uri.encodeComponent(crop)}&district=${Uri.encodeComponent(location)}&state=${Uri.encodeComponent(state)}");
      if (marketRes.statusCode == 200) {
        _marketData = jsonDecode(marketRes.body);
      }

      // 3. Fetch Today's Tasks
      final farmerId = await LocalStorageService.getFarmerId();
      final taskUrl = farmerId != null && farmerId.isNotEmpty
          ? "${ApiEndpoints.tasks}/today?farmer_id=${Uri.encodeComponent(farmerId)}"
          : "${ApiEndpoints.tasks}/today";
      final tasksRes = await ApiClient.get(taskUrl);
      if (tasksRes.statusCode == 200) {
        final List<dynamic> list = jsonDecode(tasksRes.body);
        _todayTasks = list.map((e) => Map<String, dynamic>.from(e)).toList();
      }
    } catch (_) {
      // Honest offline/unavailable status; NEVER invent fake data labeled CURRENT
      _weatherData = {
        "location": location,
        "current": {
          "weather_condition": "Live weather service temporarily unavailable",
          "freshness": "UNAVAILABLE",
          "source": "Weather Service"
        }
      };
      _marketData = {
        "commodity": crop,
        "freshness": "UNAVAILABLE",
        "source": "Mandi Price Service"
      };
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _completeTask(String taskId) async {
    try {
      final farmerId = await LocalStorageService.getFarmerId() ?? "farmer_demo_1";
      final res = await ApiClient.post("${ApiEndpoints.tasks}/$taskId/complete", {
        "farmer_id": farmerId,
        "farm_id": "farm_1",
        "completion_source": "WEB"
      });
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Task marked COMPLETED!"), backgroundColor: AppColors.primaryGreen),
        );
        _loadDashboardData();
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Action failed: $e"), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _postponeTask(String taskId) async {
    try {
      final farmerId = await LocalStorageService.getFarmerId() ?? "farmer_demo_1";
      final res = await ApiClient.post("${ApiEndpoints.tasks}/$taskId/postpone", {
        "farmer_id": farmerId,
        "farm_id": "farm_1",
        "days_to_postpone": 2,
        "reason": "Postponed via Dashboard"
      });
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Task postponed by 2 days."), backgroundColor: Colors.blue),
        );
        _loadDashboardData();
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Action failed: $e"), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _skipTaskWithConfirmation(Map<String, dynamic> task) async {
    final title = task['title'] ?? 'Task';
    final taskId = task['task_id'] ?? '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.orange),
            SizedBox(width: 8),
            Text("Confirm Task Skip"),
          ],
        ),
        content: Text(
          "Skipping '$title' may impact crop development because soil moisture is low and rain is uncertain.\n\nDo you still want to skip this task?",
          style: const TextStyle(fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text("NO, CANCEL"),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text("YES, SKIP"),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        final res = await ApiClient.post("${ApiEndpoints.tasks}/$taskId/skip", {
          "farmer_id": "farmer_demo_1",
          "farm_id": "farm_demo_1",
          "reason": "Farmer confirmed skip on web dashboard"
        });
        if (res.statusCode == 200) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Task skipped as requested."), backgroundColor: Colors.orange),
          );
          _loadDashboardData();
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Skip failed: $e"), backgroundColor: Colors.red),
        );
      }
    }
  }

  void _askSampleQuestion(String question) {
    Navigator.pushNamed(context, AppRouter.chat, arguments: question);
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppColors.primaryGreen,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.eco, color: Colors.white, size: 20),
            ),
            const SizedBox(width: 8),
            const Text("BHOOMI", style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.0)),
          ],
        ),
        actions: [
          // Language Switcher Dropdown
          Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            padding: const EdgeInsets.symmetric(horizontal: 10),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.18),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.white30),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _currentLanguage,
                dropdownColor: AppColors.primaryGreen,
                icon: const Icon(Icons.language, color: Colors.white, size: 18),
                items: _languageNames.entries.map((entry) {
                  return DropdownMenuItem(
                    value: entry.key,
                    child: Text(entry.value, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) _changeLanguage(val);
                },
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.chat_bubble_outline),
            tooltip: "Chat Assistant",
            onPressed: () => Navigator.pushNamed(context, AppRouter.chat),
          ),
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: "Farm Profile",
            onPressed: () => Navigator.pushNamed(context, AppRouter.farmProfile),
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            tooltip: "Logout / Login",
            onPressed: () async {
              await LocalStorageService.clear();
              if (mounted) {
                Navigator.pushNamedAndRemoveUntil(context, AppRouter.auth, (route) => false);
              }
            },
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadDashboardData,
          color: AppColors.primaryGreen,
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 960),
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (_isLoading) const LinearProgressIndicator(color: AppColors.primaryGreen),

                    // Desktop Web Navigation Bar (Screen width >= 800)
                    if (MediaQuery.of(context).size.width >= 800)
                      Container(
                        margin: const EdgeInsets.only(bottom: 20),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppColors.dividerColor),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 6, offset: const Offset(0, 2)),
                          ],
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                          children: [
                            _buildNavTab(loc?.translate("home") ?? "Home", Icons.home_rounded, true, () {}),
                            _buildNavTab(loc?.translate("my_farm") ?? "My Farm", Icons.agriculture_rounded, false, () => Navigator.pushNamed(context, AppRouter.farmProfile)),
                            _buildNavTab(loc?.translate("tasks") ?? "Tasks", Icons.checklist_rounded, false, () => Navigator.pushNamed(context, AppRouter.tasks)),
                            _buildNavTab(loc?.translate("weather") ?? "Weather", Icons.cloud_outlined, false, () => Navigator.pushNamed(context, AppRouter.weather)),
                            _buildNavTab(loc?.translate("market") ?? "Market", Icons.storefront_rounded, false, () => Navigator.pushNamed(context, AppRouter.market)),
                            _buildNavTab(loc?.translate("crop_health") ?? "Crop Health", Icons.camera_alt_outlined, false, () => Navigator.pushNamed(context, AppRouter.leafScanner)),
                            _buildNavTab(loc?.translate("profit") ?? "Profit", Icons.calculate_outlined, false, () => Navigator.pushNamed(context, AppRouter.profitSimulator)),
                            _buildNavTab(loc?.translate("voice_assistant") ?? "Voice Assistant", Icons.mic_rounded, false, () => Navigator.pushNamed(context, AppRouter.voiceAssistant)),
                          ],
                        ),
                      ),

                    // 1. Farmer Greeting & Farm Header
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "${loc?.translate("good_morning") ?? "Good morning"}, ${_farmerName.isNotEmpty ? _farmerName : (loc?.translate("farmer") ?? "Farmer")}",
                              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppColors.textDark),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              loc?.translate("your_farm_today") ?? "Your Farm Today — AI Farm Manager",
                              style: const TextStyle(fontSize: 14, color: AppColors.textMuted, fontWeight: FontWeight.w500),
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.primaryGreen.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.location_on, size: 14, color: AppColors.primaryGreen),
                              const SizedBox(width: 4),
                              Text(
                                _farmerLocation.isNotEmpty ? _farmerLocation : (loc?.translate("my_farm") ?? "My Farm"),
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.primaryGreen),
                              ),
                            ],
                          ),
                        )
                      ],
                    ),
                    const SizedBox(height: 20),

                    // 2. Central Voice-First Interaction Card (Reference 1)
                    Container(
                      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: AppColors.primaryGreen.withOpacity(0.25), width: 1.5),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.primaryGreen.withOpacity(0.06),
                            blurRadius: 16,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Column(
                        children: [
                          Text(
                            loc?.translate("what_would_you_like_to_know") ?? "What would you like to know?",
                            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.textDark),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            loc?.translate("here_to_help") ?? "I'm here to help.",
                            style: const TextStyle(fontSize: 14, color: AppColors.textMuted, fontWeight: FontWeight.w500),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 20),

                          // Large Central Voice Orb
                          Center(
                            child: VoiceOrb(
                              state: _voiceState,
                              onTap: () => Navigator.pushNamed(context, AppRouter.voiceAssistant),
                              size: 120,
                            ),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.primaryGreen,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                              elevation: 2,
                            ),
                            icon: const Icon(Icons.mic, size: 18),
                            label: Text(
                              loc?.translate("tap_and_speak") ?? "TAP AND SPEAK",
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.0),
                            ),
                            onPressed: () => Navigator.pushNamed(context, AppRouter.voiceAssistant),
                          ),
                          const SizedBox(height: 16),
                          const Text(
                            "or select an agricultural decision below:",
                            style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                          ),
                          const SizedBox(height: 10),

                          // Conversational Quick Chips
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            alignment: WrapAlignment.center,
                            children: [
                              _buildScenarioChip("What should I do today?"),
                              _buildScenarioChip("Should I irrigate today?"),
                              _buildScenarioChip("Is rain expected today?"),
                              _buildScenarioChip("Which crop is suited for black soil?"),
                              _buildScenarioChip("Should I sell now?"),
                              _buildScenarioChip("What changed on my farm?"),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // 3. Farm Digital Twin Summary
                    Container(
                      padding: const EdgeInsets.all(16.0),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16.0),
                        border: Border.all(color: AppColors.dividerColor),
                        boxShadow: [
                          BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 8, offset: const Offset(0, 3)),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                "🌱 ${loc?.translate("my_farm") ?? "MY FARM DIGITAL TWIN"}",
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, letterSpacing: 0.5),
                              ),
                              InkWell(
                                onTap: () => Navigator.pushNamed(context, AppRouter.farmProfile),
                                child: const Text("Edit Profile", style: TextStyle(color: AppColors.primaryGreen, fontWeight: FontWeight.bold, fontSize: 13)),
                              ),
                            ],
                          ),
                          const Divider(height: 18),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceAround,
                            children: [
                              _buildFarmInfoItem(loc?.translate("crop") ?? "Crop", "Chilli (Teja)"),
                              _buildFarmInfoItem(loc?.translate("area") ?? "Area", "3.0 Acres"),
                              _buildFarmInfoItem(loc?.translate("stage") ?? "Stage", "Vegetative"),
                              _buildFarmInfoItem(loc?.translate("location") ?? "Location", "Guntur (AP)"),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // 4. Quick Actions
                    Text(
                      loc?.translate("quick_actions") ?? "QUICK ACTIONS",
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.textMuted),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _buildQuickAction(Icons.cloud_outlined, loc?.translate("weather") ?? "Weather", AppColors.skyBlue, () {
                          Navigator.pushNamed(context, AppRouter.weather);
                        }),
                        const SizedBox(width: 12),
                        _buildQuickAction(Icons.monetization_on_outlined, loc?.translate("market") ?? "Market", AppColors.accentGold, () {
                          Navigator.pushNamed(context, AppRouter.market);
                        }),
                        const SizedBox(width: 12),
                        _buildQuickAction(Icons.calculate_outlined, loc?.translate("profit_simulator") ?? "Profit Sim", AppColors.primaryGreen, () {
                          Navigator.pushNamed(context, AppRouter.profitSimulator);
                        }),
                        const SizedBox(width: 12),
                        _buildQuickAction(Icons.camera_alt_outlined, "Health Scan", AppColors.soilBrown, () {
                          Navigator.pushNamed(context, AppRouter.leafScanner);
                        }),
                        const SizedBox(width: 12),
                        _buildQuickAction(Icons.checklist_rounded, "Tasks", AppColors.warningOrange, () {
                          Navigator.pushNamed(context, AppRouter.tasks);
                        }),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // 5. Today's Tasks
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          loc?.translate("tasks_today") ?? "TODAY'S PRIORITIES",
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.textMuted),
                        ),
                        InkWell(
                          onTap: () => Navigator.pushNamed(context, AppRouter.tasks),
                          child: Text(loc?.translate("view_all") ?? "View All", style: const TextStyle(color: AppColors.primaryGreen, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    if (_todayTasks.isNotEmpty)
                      ..._todayTasks.map((t) {
                        final isDone = (t['status'] ?? '').toString().toUpperCase() == 'COMPLETED';
                        final taskId = t['task_id'] ?? '';
                        return Container(
                          margin: const EdgeInsets.symmetric(vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.grey[200]!),
                          ),
                          child: ListTile(
                            leading: IconButton(
                              icon: Icon(
                                isDone ? Icons.check_circle : Icons.radio_button_unchecked,
                                color: isDone ? AppColors.primaryGreen : Colors.grey,
                              ),
                              onPressed: isDone ? null : () => _completeTask(taskId),
                            ),
                            title: Text(
                              t['title'] ?? 'Task',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                                decoration: isDone ? TextDecoration.lineThrough : null,
                                color: isDone ? Colors.grey : Colors.black87,
                              ),
                            ),
                            subtitle: Text(
                              "${t['reason'] ?? t['description'] ?? ''} • Due: ${t['due_at'] != null ? t['due_at'].toString().substring(0, 10) : 'Today'}",
                              style: const TextStyle(fontSize: 12),
                            ),
                            trailing: isDone
                                ? Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: AppColors.primaryGreen.withOpacity(0.12),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: const Text("COMPLETED", style: TextStyle(color: AppColors.primaryGreen, fontWeight: FontWeight.bold, fontSize: 11)),
                                  )
                                : Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      TextButton(
                                        onPressed: () => _postponeTask(taskId),
                                        child: const Text("Postpone", style: TextStyle(fontSize: 12, color: Colors.blue)),
                                      ),
                                      TextButton(
                                        onPressed: () => _skipTaskWithConfirmation(t),
                                        child: const Text("Skip", style: TextStyle(fontSize: 12, color: Colors.orange)),
                                      ),
                                    ],
                                  ),
                          ),
                        );
                      }).toList()
                    else ...[
                      TaskCard(
                        title: "Inspect underside of leaves for early thrips",
                        subtitle: "Vegetative stage scouting (10 plants per acre)",
                        dueDate: "Today",
                        priority: "high",
                      ),
                      TaskCard(
                        title: "Check soil moisture before afternoon showers",
                        subtitle: "Defer surface irrigation if rain occurs",
                        dueDate: "Today",
                        priority: "medium",
                      ),
                    ],

                    const SizedBox(height: 24),

                    // 6. Weather Live Card (Tap to open full weather screen)
                    if (_weatherData != null)
                      InkWell(
                        onTap: () => Navigator.pushNamed(context, AppRouter.weather),
                        borderRadius: BorderRadius.circular(16),
                        child: WeatherCard(data: _weatherData!),
                      ),
                    const SizedBox(height: 16),

                    // 7. Mandi Realization Card (Tap to open full market screen)
                    if (_marketData != null)
                      InkWell(
                        onTap: () => Navigator.pushNamed(context, AppRouter.market),
                        borderRadius: BorderRadius.circular(16),
                        child: MarketCard(data: _marketData!),
                      ),
                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: 0,
        selectedItemColor: AppColors.primaryGreen,
        unselectedItemColor: Colors.grey.shade600,
        type: BottomNavigationBarType.fixed,
        backgroundColor: Colors.white,
        elevation: 8,
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
        unselectedLabelStyle: const TextStyle(fontSize: 11),
        onTap: (index) {
          if (index == 1) Navigator.pushNamed(context, AppRouter.voiceAssistant);
          if (index == 2) Navigator.pushNamed(context, AppRouter.tasks);
          if (index == 3) Navigator.pushNamed(context, AppRouter.farmProfile);
          if (index == 4) Navigator.pushNamed(context, AppRouter.farmProfile);
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home_rounded), label: "Home"),
          BottomNavigationBarItem(icon: Icon(Icons.mic_rounded), label: "Voice"),
          BottomNavigationBarItem(icon: Icon(Icons.checklist_rounded), label: "Tasks"),
          BottomNavigationBarItem(icon: Icon(Icons.agriculture_rounded), label: "Farm"),
          BottomNavigationBarItem(icon: Icon(Icons.person_rounded), label: "Profile"),
        ],
      ),
    );
  }

  Widget _buildScenarioChip(String text) {
    return ActionChip(
      label: Text(text, style: const TextStyle(fontSize: 12, color: AppColors.textDark)),
      backgroundColor: Colors.white,
      side: BorderSide(color: AppColors.primaryGreen.withOpacity(0.3)),
      avatar: const Icon(Icons.arrow_forward_ios_rounded, size: 10, color: AppColors.primaryGreen),
      onPressed: () => _askSampleQuestion(text),
    );
  }

  Widget _buildFarmInfoItem(String title, String value) {
    return Column(
      children: [
        Text(title, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppColors.textDark)),
      ],
    );
  }

  Widget _buildQuickAction(IconData icon, String label, Color color, VoidCallback onTap) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12.0),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14.0),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12.0),
            border: Border.all(color: AppColors.dividerColor),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 4, offset: const Offset(0, 2)),
            ],
          ),
          child: Column(
            children: [
              Icon(icon, color: color, size: 24),
              const SizedBox(height: 6),
              Text(
                label,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textDark),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNavTab(String label, IconData icon, bool isActive, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isActive ? AppColors.lightGreen : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(icon, size: 16, color: isActive ? AppColors.primaryGreen : AppColors.textMuted),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 13,
                fontWeight: isActive ? FontWeight.bold : FontWeight.w500,
                color: isActive ? AppColors.primaryGreen : AppColors.textDark,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
