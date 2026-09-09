import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';
import '../../core/storage/secure_storage.dart';
import '../../routing/app_router.dart';

class OnboardingScreen extends StatefulWidget {
  final Function(Locale)? onLanguageChanged;
  const OnboardingScreen({Key? key, this.onLanguageChanged}) : super(key: key);

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  // Screen state: 0 = Hero Screen (Reference 2), 1 = Farm Setup Screen
  int _currentStep = 0;

  String _currentLanguage = "en";

  // Form Controllers
  final _nameController = TextEditingController();
  final _locationController = TextEditingController();
  final _areaController = TextEditingController();
  final _varietyController = TextEditingController();
  final _sowingDateController = TextEditingController();

  String _selectedSoil = "black";
  String _selectedIrrigation = "borewell";
  String _selectedCrop = "Chilli";
  bool _isLoading = false;
  String? _errorMessage;

  final List<Map<String, String>> _languages = const [
    {"code": "en", "label": "English"},
    {"code": "te", "label": "తెలుగు"},
    {"code": "hi", "label": "हिन्दी"},
    {"code": "ta", "label": "தமிழ்"},
    {"code": "kn", "label": "ಕನ್ನಡ"},
    {"code": "ml", "label": "മലയാളം"},
  ];

  final Map<String, Map<String, String>> _translations = {
    "en": {
      "headline_1": "YOUR FARM.",
      "headline_2": "SMARTER.",
      "subtitle": "Your personal AI farm manager for decisions, tasks and crop care.",
      "choose_language": "Choose your language",
      "get_started": "GET STARTED",
      "farm_setup_title": "Set Up Your Farm Digital Twin",
      "farm_setup_sub": "Enter your farm details to receive personalized, autonomous agronomic decisions.",
      "farmer_name": "Farmer Name",
      "location": "Location (Village, District)",
      "farm_area": "Farm Area (Acres)",
      "soil_type": "Soil Type",
      "irrigation": "Irrigation Source",
      "crop": "Primary Crop",
      "variety": "Crop Variety",
      "sowing_date": "Sowing / Transplant Date",
      "save_continue": "SAVE & ENTER FARM",
      "saving": "Setting up Farm Twin...",
    },
    "te": {
      "headline_1": "మీ పొలం.",
      "headline_2": "మరింత స్మార్ట్.",
      "subtitle": "పంట నిర్ణయాలు, పనులు మరియు సంరక్షణ కోసం మీ వ్యక్తిగత AI వ్యవసాయ మేనేజర్.",
      "choose_language": "మీ భాషను ఎంచుకోండి",
      "get_started": "ప్రారంభించండి",
      "farm_setup_title": "మీ పొలం డిజిటల్ ట్విన్ వివరాలు",
      "farm_setup_sub": "వ్యక్తిగత వ్యవసాయ సలహాలు పొందడానికి మీ పొలం వివరాలను నమోదు చేయండి.",
      "farmer_name": "రైతు పేరు",
      "location": "ప్రాంతం (గ్రామం, జిల్లా)",
      "farm_area": "విస్తీర్ణం (ఎకరాలు)",
      "soil_type": "నేల రకం",
      "irrigation": "నీటి వనరు",
      "crop": "పంట",
      "variety": "వంగడం / రకం",
      "sowing_date": "విత్తిన తేదీ",
      "save_continue": "భద్రపరచి కొనసాగండి",
      "saving": "పొలం వివరాలు భద్రపరుస్తున్నాము...",
    },
    "hi": {
      "headline_1": "आपका खेत.",
      "headline_2": "अधिक स्मार्ट.",
      "subtitle": "सटीक निर्णयों, दैनिक कार्यों और फसल सुरक्षा के लिए आपका व्यक्तिगत AI फार्म मैनेजर।",
      "choose_language": "अपनी भाषा चुनें",
      "get_started": "शुरू करें",
      "farm_setup_title": "फार्म डिजिटल ट्विन सेटअप",
      "farm_setup_sub": "सटीक कृषि सलाह पाने के लिए अपने खेत का विवरण दर्ज करें।",
      "farmer_name": "किसान का नाम",
      "location": "स्थान (गाँव, जिला)",
      "farm_area": "खेत का क्षेत्रफल (एकड़)",
      "soil_type": "मिट्टी का प्रकार",
      "irrigation": "सिंचाई का साधन",
      "crop": "मुख्य फसल",
      "variety": "किस्म (वैरायटी)",
      "sowing_date": "बुवाई की तिथि",
      "save_continue": "सहेजें और आगे बढ़ें",
      "saving": "खेत का डेटा सुरक्षित हो रहा है...",
    },
    "ta": {
      "headline_1": "உங்கள் பண்ணை.",
      "headline_2": "ஸ்மார்ட்டர்.",
      "subtitle": "பயிர் முடிவுகள் மற்றும் பணிகளுக்கான உங்கள் AI பண்ணை மேலாளர்.",
      "choose_language": "மொழியைத் தேர்ந்தெடுக்கவும்",
      "get_started": "தொடங்குங்கள்",
      "farm_setup_title": "பண்ணை விவரங்கள்",
      "farm_setup_sub": "சரியான ஆலோசனைக்கு பண்ணை விவரங்களை உள்ளிடவும்.",
      "farmer_name": "விவசாயி பெயர்",
      "location": "இருப்பிடம்",
      "farm_area": "பரப்பளவு (ஏக்கர்)",
      "soil_type": "மண் வகை",
      "irrigation": "பாசன முறை",
      "crop": "பயிர்",
      "variety": "பயிர் ரகம்",
      "sowing_date": "விதைத்த தேதி",
      "save_continue": "சேமித்து தொடரவும்",
      "saving": "சேமிக்கப்படுகிறது...",
    },
    "kn": {
      "headline_1": "ನಿಮ್ಮ ಜಮೀನು.",
      "headline_2": "ಸ್ಮಾರ್ಟ್.",
      "subtitle": "ಬೆಳೆ ನಿರ್ಧಾರಗಳು ಮತ್ತು ಆರೈಕೆಗಾಗಿ ನಿಮ್ಮ ವೈಯಕ್ತಿಕ AI ಕೃಷಿ ವ್ಯವಸ್ಥಾಪಕ.",
      "choose_language": "ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆಮಾಡಿ",
      "get_started": "ಪ್ರಾರಂಭಿಸಿ",
      "farm_setup_title": "ಕೃಷಿ ಡಿಜಿಟಲ್ ಟ್ವಿನ್",
      "farm_setup_sub": "ವೈಯಕ್ತಿಕ ಸಲಹೆಗಳಿಗಾಗಿ ನಿಮ್ಮ ಕೃಷಿ ವಿವರಗಳನ್ನು ನಮೂದಿಸಿ.",
      "farmer_name": "ರೈತರ ಹೆಸರು",
      "location": "ಸ್ಥಳ",
      "farm_area": "ವಿಸ್ತೀರ್ಣ (ಎಕರೆ)",
      "soil_type": "ಮಣ್ಣಿನ ವಿಧ",
      "irrigation": "ನೀರಾವರಿ ಮೂಲ",
      "crop": "ಬೆಳೆ",
      "variety": "ತಳಿ",
      "sowing_date": "ಬಿತ್ತನೆ ದಿನಾಂಕ",
      "save_continue": "ಉಳಿಸಿ ಮುಂದುವರಿಯಿರಿ",
      "saving": "ಉಳಿಸಲಾಗುತ್ತಿದೆ...",
    },
    "ml": {
      "headline_1": "നിങ്ങളുടെ കൃഷിഭൂമി.",
      "headline_2": "കൂടുതൽ സ്മാർട്ട്.",
      "subtitle": "തീരുമാനങ്ങൾക്കും വിള സംരക്ഷണത്തിനുമുള്ള നിങ്ങളുടെ AI ഫാം മാനേജർ.",
      "choose_language": "ഭാഷ തിരഞ്ഞെടുക്കുക",
      "get_started": "ആരംഭിക്കുക",
      "farm_setup_title": "ഡിജിറ്റൽ ട്വിൻ സജ്ജീകരിക്കുക",
      "farm_setup_sub": "കൃത്യമായ നിർദ്ദേശങ്ങൾ ലഭിക്കാൻ വിവരങ്ങൾ നൽകുക.",
      "farmer_name": "കർഷകന്റെ പേര്",
      "location": "സ്ഥലം",
      "farm_area": "വിസ്തീർണ്ണം (ഏക്കർ)",
      "soil_type": "മണ്ണിന്റെ തരം",
      "irrigation": "നനയ്ക്കൽ രീതി",
      "crop": "വിള",
      "variety": "ഇനം",
      "sowing_date": "വിതച്ച തീയതി",
      "save_continue": "സംരക്ഷിച്ച് തുടരുക",
      "saving": "സംരക്ഷിക്കുന്നു...",
    },
  };

  final List<String> _soils = ["black", "red", "alluvial", "sandy", "clay", "loamy"];
  final List<String> _irrigations = ["borewell", "canal", "drip", "sprinkler", "rainfed"];
  final List<String> _crops = ["Chilli", "Cotton", "Rice / Paddy", "Maize", "Groundnut", "Turmeric"];

  @override
  void initState() {
    super.initState();
    _loadStoredLanguage();
  }

  Future<void> _loadStoredLanguage() async {
    final lang = await LocalStorageService.getLanguage();
    setState(() => _currentLanguage = lang);
  }

  String _t(String key) {
    return _translations[_currentLanguage]?[key] ?? _translations["en"]![key] ?? key;
  }

  Future<void> _selectLanguage(String langCode) async {
    await LocalStorageService.setLanguage(langCode);
    setState(() {
      _currentLanguage = langCode;
    });
    widget.onLanguageChanged?.call(Locale(langCode));
  }

  Future<void> _saveFarmSetup() async {
    final areaVal = double.tryParse(_areaController.text.trim());
    if (areaVal == null || areaVal <= 0) {
      setState(() => _errorMessage = "Please enter a valid farm area (e.g. 3.0 acres).");
      return;
    }
    if (_nameController.text.trim().isEmpty) {
      setState(() => _errorMessage = "Please enter farmer name.");
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // 1. Save to LocalStorageService
      await LocalStorageService.saveFarmProfile(
        name: _nameController.text.trim(),
        location: _locationController.text.trim(),
        area: _areaController.text.trim(),
        crop: _selectedCrop,
        variety: _varietyController.text.trim(),
        soil: _selectedSoil,
        irrigation: _selectedIrrigation,
        sowingDate: _sowingDateController.text.trim(),
      );

      // 2. Persist to Backend API
      final farmBody = {
        "farm_name": "Main Farm",
        "total_area_acres": areaVal,
        "latitude": 16.3067,
        "longitude": 80.4365,
        "soil_type": _selectedSoil,
        "irrigation_source": _selectedIrrigation,
        "language": _currentLanguage,
      };

      final response = await ApiClient.post(ApiEndpoints.farms, farmBody);
      if (response.statusCode == 200) {
        final farmData = jsonDecode(response.body);
        final farmId = farmData['id'];
        await ApiClient.post("${ApiEndpoints.farms}/$farmId/crops", {
          "crop_name": _selectedCrop,
          "area_acres": areaVal,
          "current_stage": "vegetative",
          "variety": _varietyController.text.trim(),
          "language": _currentLanguage,
        });
      }
    } catch (_) {
      // Graceful offline fallback
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
        Navigator.pushReplacementNamed(context, AppRouter.home);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      body: SafeArea(
        child: _currentStep == 0 ? _buildHeroScreen() : _buildSetupScreen(),
      ),
    );
  }

  // Reference 2: Full-screen Agricultural Visual Hero Experience
  Widget _buildHeroScreen() {
    return Container(
      width: double.infinity,
      height: double.infinity,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFF1B5E20), // Deep Forest Green
            const Color(0xFF2E7D32), // Lush Green
            const Color(0xFF003300), // Deep Soil
          ],
        ),
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Top Header: App Branding & Language Chips
                Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.white24,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Icon(Icons.eco, color: Colors.white, size: 24),
                            ),
                            const SizedBox(width: 10),
                            const Text(
                              "BHOOMI",
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 20,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 1.5,
                              ),
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white12,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.white24),
                          ),
                          child: const Text(
                            "AI FARM MANAGER",
                            style: TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),

                    // Early Language Selector
                    Text(
                      _t("choose_language"),
                      style: const TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      alignment: WrapAlignment.center,
                      children: _languages.map((l) {
                        final isSel = _currentLanguage == l["code"];
                        return ChoiceChip(
                          label: Text(l["label"]!),
                          selected: isSel,
                          selectedColor: AppColors.accentGold,
                          backgroundColor: Colors.white12,
                          labelStyle: TextStyle(
                            color: isSel ? Colors.black87 : Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                          onSelected: (_) => _selectLanguage(l["code"]!),
                        );
                      }).toList(),
                    ),
                  ],
                ),

                // Center: Reference 2 Strong Typography Hero
                Column(
                  children: [
                    Container(
                      width: 100,
                      height: 100,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white.withOpacity(0.15),
                        border: Border.all(color: Colors.white38, width: 2),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.2),
                            blurRadius: 20,
                            spreadRadius: 4,
                          ),
                        ],
                      ),
                      child: const Center(
                        child: Icon(Icons.agriculture_rounded, color: Colors.white, size: 54),
                      ),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      _t("headline_1"),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 38,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2.0,
                        height: 1.1,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    Text(
                      _t("headline_2"),
                      style: TextStyle(
                        color: AppColors.accentGold,
                        fontSize: 38,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2.0,
                        height: 1.1,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      _t("subtitle"),
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 16,
                        height: 1.4,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),

                // Bottom: Prominent GET STARTED Action
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: AppColors.deepGreen,
                      elevation: 6,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    ),
                    onPressed: () {
                      setState(() => _currentStep = 1);
                    },
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          _t("get_started"),
                          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, letterSpacing: 1.2),
                        ),
                        const SizedBox(width: 8),
                        const Icon(Icons.arrow_forward_rounded, size: 20),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // Step 2: Farm Setup with full validated fields
  Widget _buildSetupScreen() {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: Text(_t("farm_setup_title")),
        backgroundColor: AppColors.primaryGreen,
        foregroundColor: Colors.white,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => setState(() => _currentStep = 0),
        ),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _t("farm_setup_sub"),
                  style: const TextStyle(fontSize: 14, color: AppColors.textMuted),
                ),
                const SizedBox(height: 20),

                if (_errorMessage != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(10)),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, color: Colors.red, size: 18),
                        const SizedBox(width: 8),
                        Expanded(child: Text(_errorMessage!, style: const TextStyle(color: Colors.red, fontSize: 13))),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Farmer Name
                TextField(
                  controller: _nameController,
                  decoration: InputDecoration(
                    labelText: _t("farmer_name"),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    filled: true,
                    fillColor: Colors.white,
                    prefixIcon: const Icon(Icons.person_outline, color: AppColors.primaryGreen),
                  ),
                ),
                const SizedBox(height: 16),

                // Location
                TextField(
                  controller: _locationController,
                  decoration: InputDecoration(
                    labelText: _t("location"),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    filled: true,
                    fillColor: Colors.white,
                    prefixIcon: const Icon(Icons.location_on_outlined, color: AppColors.primaryGreen),
                  ),
                ),
                const SizedBox(height: 16),

                // Farm Area
                TextField(
                  controller: _areaController,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: _t("farm_area"),
                    suffixText: "Acres",
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    filled: true,
                    fillColor: Colors.white,
                    prefixIcon: const Icon(Icons.aspect_ratio_outlined, color: AppColors.primaryGreen),
                  ),
                ),
                const SizedBox(height: 20),

                // Soil Type Chips
                Text(_t("soil_type"), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: _soils.map((soil) {
                    final isSel = _selectedSoil == soil;
                    return ChoiceChip(
                      label: Text(soil.toUpperCase()),
                      selected: isSel,
                      selectedColor: AppColors.primaryGreen,
                      labelStyle: TextStyle(
                        color: isSel ? Colors.white : AppColors.textDark,
                        fontWeight: FontWeight.w600,
                      ),
                      onSelected: (selected) {
                        if (selected) setState(() => _selectedSoil = soil);
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 20),

                // Irrigation Source Chips
                Text(_t("irrigation"), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: _irrigations.map((irr) {
                    final isSel = _selectedIrrigation == irr;
                    return ChoiceChip(
                      label: Text(irr.toUpperCase()),
                      selected: isSel,
                      selectedColor: AppColors.primaryGreen,
                      labelStyle: TextStyle(
                        color: isSel ? Colors.white : AppColors.textDark,
                        fontWeight: FontWeight.w600,
                      ),
                      onSelected: (selected) {
                        if (selected) setState(() => _selectedIrrigation = irr);
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 20),

                // Primary Crop Dropdown
                Text(_t("crop"), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _selectedCrop,
                  items: _crops.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => _selectedCrop = val);
                  },
                  decoration: InputDecoration(
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                ),
                const SizedBox(height: 16),

                // Variety & Sowing Date
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _varietyController,
                        decoration: InputDecoration(
                          labelText: _t("variety"),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          filled: true,
                          fillColor: Colors.white,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _sowingDateController,
                        decoration: InputDecoration(
                          labelText: _t("sowing_date"),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          filled: true,
                          fillColor: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 32),

                // Submit Button
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primaryGreen,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      elevation: 4,
                    ),
                    onPressed: _isLoading ? null : _saveFarmSetup,
                    child: _isLoading
                        ? Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)),
                              const SizedBox(width: 12),
                              Text(_t("saving"), style: const TextStyle(fontWeight: FontWeight.bold)),
                            ],
                          )
                        : Text(
                            _t("save_continue"),
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.8),
                          ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
