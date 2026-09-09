import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';
import '../../core/storage/secure_storage.dart';
import '../../routing/app_router.dart';
import '../../shared/widgets/voice_orb.dart';
import '../../shared/cards/weather_card.dart';
import '../../shared/cards/market_card.dart';
import '../../shared/cards/profit_card.dart';
import '../../shared/cards/simulation_card.dart';
import '../../shared/cards/risk_card.dart';
import '../../shared/cards/crop_recommendation_card.dart';

class ChatMessageModel {
  final String sender; // user, assistant
  final String content;
  final List<dynamic> visualCards;
  final DateTime timestamp;

  ChatMessageModel({
    required this.sender,
    required this.content,
    this.visualCards = const [],
    required this.timestamp,
  });
}

class ChatSuggestion {
  final String icon;
  final String label;
  final String query;

  const ChatSuggestion({
    required this.icon,
    required this.label,
    required this.query,
  });
}

class ChatScreen extends StatefulWidget {
  final String? initialQuery;
  const ChatScreen({Key? key, this.initialQuery}) : super(key: key);

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessageModel> _messages = [];
  bool _isLoading = false;
  String _currentLanguage = "en";

  static const Map<String, String> _initialGreetings = {
    "te": "నమస్కారం! నేను భూమి, మీ AI వ్యవసాయ సహాయకుడిని. మీ పంటల వివరాలు, వాతావరణం, లేదా మార్కెట్ ధరల గురించి నన్ను అడగవచ్చు.",
    "hi": "नमस्ते! मैं भूमि हूँ, आपका AI कृषि मित्र। आज आपकी फसल, मौसम, या मंडी भाव के बारे में कोई भी प्रश्न पूछें।",
    "ta": "வணக்கம்! நான் பூமி, உங்கள் AI விவசாய உதவியாளர். பயிர் நலம், வானிலை, அல்லது சந்தை விலை பற்றி கேட்கலாம்.",
    "kn": "ನಮಸ್ಕಾರ! ನಾನು ಭೂಮಿ, ನಿಮ್ಮ AI ಕೃಷಿ ಮಿತ್ರ. ಬೆಳೆ, ಹವಾಮಾನ ಅಥವಾ ಮಾರುಕಟ್ಟೆ ದರಗಳ ಬಗ್ಗೆ ಕೇಳಿ.",
    "ml": "നമസ്കാരം! ഞാൻ ഭൂമി, നിങ്ങളുടെ AI കാർഷിക സഹായി. വിളകൾ, കാലാവസ്ഥ അല്ലെങ്കിൽ വിപണി വില സംബന്ധിച്ച് ചോദിക്കാം.",
    "en": "Namaskaram! I am BHOOMI, your Personal AI Farm Manager. Ask me anything about weather, irrigation, tasks, market prices, or crop health.",
  };

  static const Map<String, List<ChatSuggestion>> _suggestionsByLang = {
    "te": [
      ChatSuggestion(icon: "📋", label: "ఈరోజు ఏం చేయాలి?", query: "ఈరోజు నా పొలంలో ఏం చేయాలి?"),
      ChatSuggestion(icon: "🌧️", label: "వర్షం పడుతుందా?", query: "ఈరోజు వర్షం పడుతుందా?"),
      ChatSuggestion(icon: "💧", label: "నీరు పెట్టాలా?", query: "నేను నీరు పెట్టాలా?"),
      ChatSuggestion(icon: "💰", label: "ఇప్పుడు అమ్మవచ్చా?", query: "ఇప్పుడు పంట అమ్మవచ్చా?"),
      ChatSuggestion(icon: "🌿", label: "పంట పరిస్థితి?", query: "నా పంట పరిస్థితి ఎలా ఉంది?"),
      ChatSuggestion(icon: "🔄", label: "పొలంలో మార్పులు?", query: "నా పొలంలో ఏం మారింది?"),
    ],
    "hi": [
      ChatSuggestion(icon: "📋", label: "आज क्या करना चाहिए?", query: "आज मुझे खेत में क्या करना चाहिए?"),
      ChatSuggestion(icon: "🌧️", label: "क्या बारिश होगी?", query: "क्या आज बारिश होगी?"),
      ChatSuggestion(icon: "💧", label: "सिंचाई सलाह?", query: "क्या मुझे सिंचाई करनी चाहिए?"),
      ChatSuggestion(icon: "💰", label: "क्या अभी बेचना चाहिए?", query: "क्या मुझे अभी बेचना चाहिए?"),
      ChatSuggestion(icon: "🌿", label: "फसल की स्थिति?", query: "मेरी फसल कैसी है?"),
      ChatSuggestion(icon: "🔄", label: "खेत में बदलाव?", query: "मेरे खेत में क्या बदलाव हुआ?"),
    ],
    "ta": [
      ChatSuggestion(icon: "📋", label: "இன்று என்ன செய்ய வேண்டும்?", query: "இன்று நான் என்ன செய்ய வேண்டும்?"),
      ChatSuggestion(icon: "🌧️", label: "மழை பெய்யுமா?", query: "இன்று மழை பெய்யுமா?"),
      ChatSuggestion(icon: "💧", label: "பாசனம் செய்யலாமா?", query: "நான் பாசனம் செய்ய வேண்டுமா?"),
      ChatSuggestion(icon: "💰", label: "இப்போது விற்கலாமா?", query: "இப்போது விற்கலாமா?"),
      ChatSuggestion(icon: "🌿", label: "பயிர் நிலை என்ன?", query: "என் பயிர் எப்படி இருக்கிறது?"),
      ChatSuggestion(icon: "🔄", label: "பண்ணை மாற்றங்கள்?", query: "என் பண்ணையில் என்ன மாற்றங்கள்?"),
    ],
    "kn": [
      ChatSuggestion(icon: "📋", label: "ಇಂದು ಏನು ಮಾಡಬೇಕು?", query: "ಇಂದು ನಾನು ಏನು ಮಾಡಬೇಕು?"),
      ChatSuggestion(icon: "🌧️", label: "ಮಳೆ ಬರುತ್ತದೆಯೇ?", query: "ಇಂದು ಮಳೆ ಬರುತ್ತದೆಯೇ?"),
      ChatSuggestion(icon: "💧", label: "ನೀರಾವರಿ ಮಾಡಬೇಕೆ?", query: "ನಾನು ನೀರಾವರಿ ಮಾಡಬೇಕೆ?"),
      ChatSuggestion(icon: "💰", label: "ಈಗ ಮಾರಾಟ ಮಾಡಬೇಕೆ?", query: "ಈಗ ಮಾರಾಟ ಮಾಡಬೇಕೆ?"),
      ChatSuggestion(icon: "🌿", label: "ಬೆಳೆ ಸ್ಥಿತಿ ಹೇಗಿದೆ?", query: "ನನ್ನ ಬೆಳೆ ಹೇಗಿದೆ?"),
      ChatSuggestion(icon: "🔄", label: "ಜಮೀನಿನಲ್ಲಿ ಬದಲಾವಣೆ?", query: "ನನ್ನ ಜಮೀನಿನಲ್ಲಿ ಏನು ಬದಲಾಗಿದೆ?"),
    ],
    "ml": [
      ChatSuggestion(icon: "📋", label: "ഇന്ന് എന്ത് ചെയ്യണം?", query: "ഇന്ന് ഞാൻ എന്ത് ചെയ്യണം?"),
      ChatSuggestion(icon: "🌧️", label: "മഴ പെയ്യുമോ?", query: "ഇന്ന് മഴ പെയ്യുമോ?"),
      ChatSuggestion(icon: "💧", label: "നനയ്ക്കണമോ?", query: "ഞാൻ നനയ്ക്കണോ?"),
      ChatSuggestion(icon: "💰", label: "ഇപ്പോൾ വിൽക്കണമോ?", query: "ഇപ്പോൾ വിൽക്കണമോ?"),
      ChatSuggestion(icon: "🌿", label: "വിളയുടെ സ്ഥിതി?", query: "എന്റെ വിള എങ്ങനെയുണ്ട്?"),
      ChatSuggestion(icon: "🔄", label: "മാറ്റങ്ങൾ എന്തെല്ലാം?", query: "എന്റെ കൃഷിയിടത്തിൽ എന്ത് മാറ്റമുണ്ടായി?"),
    ],
    "en": [
      ChatSuggestion(icon: "📋", label: "What should I do today?", query: "What should I do today?"),
      ChatSuggestion(icon: "🌧️", label: "Will it rain today?", query: "Will it rain today?"),
      ChatSuggestion(icon: "💧", label: "Should I irrigate?", query: "Should I irrigate?"),
      ChatSuggestion(icon: "💰", label: "Should I sell now?", query: "Should I sell now?"),
      ChatSuggestion(icon: "🌿", label: "How is my crop?", query: "How is my crop?"),
      ChatSuggestion(icon: "🔄", label: "What changed on my farm?", query: "What changed on my farm?"),
    ],
  };

  @override
  void initState() {
    super.initState();
    _loadLanguageAndInitGreeting();
  }

  Future<void> _loadLanguageAndInitGreeting() async {
    final lang = await LocalStorageService.getLanguage();
    if (mounted) {
      setState(() {
        _currentLanguage = lang;
        _messages.clear();
        _messages.add(ChatMessageModel(
          sender: "assistant",
          content: _initialGreetings[lang] ?? _initialGreetings["en"]!,
          timestamp: DateTime.now(),
        ));
      });
      if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
        Future.microtask(() => _sendMessage(widget.initialQuery!));
      }
    }
  }

  Future<void> _changeLanguage(String newLang) async {
    await LocalStorageService.setLanguage(newLang);
    setState(() {
      _currentLanguage = newLang;
      _messages.add(ChatMessageModel(
        sender: "assistant",
        content: _initialGreetings[newLang] ?? _initialGreetings["en"]!,
        timestamp: DateTime.now(),
      ));
    });
    _scrollToBottom();
  }

  Future<void> _sendMessage([String? textToSend]) async {
    final text = textToSend ?? _textController.text.trim();
    if (text.isEmpty) return;

    _textController.clear();
    setState(() {
      _messages.add(ChatMessageModel(
        sender: "user",
        content: text,
        timestamp: DateTime.now(),
      ));
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      final response = await ApiClient.post(ApiEndpoints.chat, {
        "content": text,
        "input_mode": "text",
        "language": _currentLanguage,
      });

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final content = data['content'] ?? "";
        final cards = data['visual_cards'] ?? [];

        setState(() {
          _messages.add(ChatMessageModel(
            sender: "assistant",
            content: content,
            visualCards: cards,
            timestamp: DateTime.now(),
          ));
        });
      } else {
        final errText = response.body.isNotEmpty ? response.body : "HTTP status ${response.statusCode}";
        setState(() {
          _messages.add(ChatMessageModel(
            sender: "assistant",
            content: "⚠️ BHOOMI Service Notice (${response.statusCode}): $errText",
            timestamp: DateTime.now(),
          ));
        });
      }
    } catch (e) {
      setState(() {
        _messages.add(ChatMessageModel(
          sender: "assistant",
          content: "⚠️ Connection Error: Unable to reach backend server ($e). Please verify that the API server is active on port 8000.",
          timestamp: DateTime.now(),
        ));
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _openVoiceDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _VoiceInputSheet(
        language: _currentLanguage,
        onVoiceQuery: (spokenText) {
          Navigator.pop(ctx);
          _sendMessage(spokenText);
        },
      ),
    );
  }

  Widget _buildCardWidget(Map<String, dynamic> card) {
    final type = card['card_type'] ?? '';
    final data = card['data'] as Map<String, dynamic>? ?? {};

    switch (type) {
      case 'weather_card':
        return WeatherCard(data: data);
      case 'market_card':
        return MarketCard(data: data);
      case 'profit_card':
        return ProfitCard(data: data);
      case 'simulation_card':
        return SimulationCard(data: data);
      case 'risk_card':
        return RiskCard(data: data);
      case 'crop_recommendation_card':
        return CropRecommendationCard(data: data);
      case 'daily_briefing_card':
        return _buildDailyBriefingCard(data);
      case 'weekly_briefing_card':
        return _buildWeeklyBriefingCard(data);
      case 'tasks_status_card':
        return _buildTasksStatusCard(data);
      case 'farm_changes_card':
        return _buildFarmChangesCard(data);
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildDailyBriefingCard(Map<String, dynamic> data) {
    final crop = data['active_crop'] ?? "Chilli";
    final stage = data['growth_stage'] ?? "Vegetative / Flowering";
    final priorities = (data['today_priorities'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];
    final advisories = (data['field_advisories'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: AppColors.primaryGreen.withOpacity(0.3), width: 1.5),
        boxShadow: [
          BoxShadow(color: AppColors.primaryGreen.withOpacity(0.06), blurRadius: 8, offset: const Offset(0, 3)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(color: AppColors.lightGreen, borderRadius: BorderRadius.circular(8)),
                child: const Icon(Icons.today_rounded, color: AppColors.primaryGreen, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Daily Farm Briefing: $crop", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.textDark)),
                    Text("Crop Stage: $stage", style: const TextStyle(fontSize: 12, color: AppColors.textMuted, fontWeight: FontWeight.w500)),
                  ],
                ),
              ),
            ],
          ),
          if (priorities.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text("Top Priorities for Today:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.textDark)),
            const SizedBox(height: 6),
            ...priorities.map((p) => Padding(
              padding: const EdgeInsets.only(bottom: 4.0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("• ", style: TextStyle(color: AppColors.primaryGreen, fontWeight: FontWeight.bold)),
                  Expanded(child: Text(p, style: const TextStyle(fontSize: 13, height: 1.3))),
                ],
              ),
            )),
          ],
          if (advisories.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: AppColors.lightGreen.withOpacity(0.5), borderRadius: BorderRadius.circular(10)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: advisories.map((a) => Text("💡 $a", style: const TextStyle(fontSize: 12, color: AppColors.textDark))).toList(),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildWeeklyBriefingCard(Map<String, dynamic> data) {
    final crop = data['active_crop'] ?? "Chilli";
    final focus = data['week_focus'] ?? "Crop Protection & Moisture Monitoring";
    final schedule = (data['days_schedule'] as List<dynamic>?) ?? [];

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: Colors.blue.withOpacity(0.3), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.calendar_month_rounded, color: Colors.blue, size: 22),
              const SizedBox(width: 8),
              Text("Weekly Plan: $crop", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            ],
          ),
          const SizedBox(height: 8),
          Text("Focus: $focus", style: const TextStyle(fontSize: 13, color: AppColors.textDark, fontWeight: FontWeight.w600)),
          if (schedule.isNotEmpty) ...[
            const SizedBox(height: 10),
            ...schedule.take(4).map((s) {
              final map = s is Map<String, dynamic> ? s : {};
              return Padding(
                padding: const EdgeInsets.only(bottom: 6.0),
                child: Text("📅 ${map['day'] ?? ''}: ${map['task'] ?? ''}", style: const TextStyle(fontSize: 12)),
              );
            }),
          ],
        ],
      ),
    );
  }

  Widget _buildTasksStatusCard(Map<String, dynamic> data) {
    final pendingCount = data['pending_count'] ?? 0;
    final overdueCount = data['overdue_count'] ?? 0;
    final tasks = (data['tasks'] as List<dynamic>?) ?? [];

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: AppColors.warningOrange.withOpacity(0.3), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.checklist_rounded, color: AppColors.warningOrange, size: 22),
                  SizedBox(width: 8),
                  Text("Tasks Status", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                ],
              ),
              Row(
                children: [
                  if (overdueCount > 0)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      margin: const EdgeInsets.only(right: 6),
                      decoration: BoxDecoration(color: Colors.red.shade100, borderRadius: BorderRadius.circular(12)),
                      child: Text("$overdueCount Overdue", style: const TextStyle(color: Colors.red, fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(color: Colors.orange.shade100, borderRadius: BorderRadius.circular(12)),
                    child: Text("$pendingCount Pending", style: const TextStyle(color: Colors.orange, fontSize: 11, fontWeight: FontWeight.bold)),
                  ),
                ],
              )
            ],
          ),
          const SizedBox(height: 12),
          ...tasks.take(3).map((t) {
            final map = t is Map<String, dynamic> ? t : {};
            return Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: AppColors.scaffoldBg, borderRadius: BorderRadius.circular(8)),
              child: Row(
                children: [
                  const Icon(Icons.radio_button_unchecked, size: 16, color: AppColors.primaryGreen),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(map['title'] ?? 'Task', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
                  ),
                  Text(map['priority']?.toString().toUpperCase() ?? 'MED', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.textMuted)),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildFarmChangesCard(Map<String, dynamic> data) {
    final summary = data['farmer_summary'] ?? "Farm state is currently stable.";
    final tasksCompleted = data['tasks_completed_count'] ?? 0;
    final stageChanges = (data['stage_changes'] as List<dynamic>?) ?? [];

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16.0),
        border: Border.all(color: Colors.teal.withOpacity(0.3), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.history_edu_rounded, color: Colors.teal, size: 22),
              SizedBox(width: 8),
              Text("Farm Changes & Timeline", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            ],
          ),
          const SizedBox(height: 10),
          Text(summary, style: const TextStyle(fontSize: 13, height: 1.4)),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: Colors.teal.shade50, borderRadius: BorderRadius.circular(6)),
                child: Text("Tasks Completed: $tasksCompleted", style: const TextStyle(fontSize: 12, color: Colors.teal, fontWeight: FontWeight.bold)),
              ),
              if (stageChanges.isNotEmpty) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(6)),
                  child: Text("Stage: ${stageChanges[0]}", style: const TextStyle(fontSize: 12, color: Colors.blue, fontWeight: FontWeight.bold)),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final suggestions = _suggestionsByLang[_currentLanguage] ?? _suggestionsByLang["en"]!;

    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text("BHOOMI", style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5, fontSize: 18)),
            Text("Sri Venkateswara Farm • Guntur", style: TextStyle(fontSize: 12, color: Colors.white70, fontWeight: FontWeight.normal)),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            tooltip: "Switch Language",
            icon: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.18),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white30),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.language, size: 16, color: Colors.white),
                  const SizedBox(width: 4),
                  Text(
                    _currentLanguage.toUpperCase(),
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white),
                  ),
                ],
              ),
            ),
            onSelected: _changeLanguage,
            itemBuilder: (context) => const [
              PopupMenuItem(value: "en", child: Text("English")),
              PopupMenuItem(value: "te", child: Text("తెలుగు (Telugu)")),
              PopupMenuItem(value: "hi", child: Text("हिंदी (Hindi)")),
              PopupMenuItem(value: "ta", child: Text("தமிழ் (Tamil)")),
              PopupMenuItem(value: "kn", child: Text("ಕನ್ನಡ (Kannada)")),
              PopupMenuItem(value: "ml", child: Text("മലയാളം (Malayalam)")),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: "Farm Profile",
            onPressed: () => Navigator.pushNamed(context, AppRouter.farmProfile),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.all(16.0),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final msg = _messages[index];
                  final isUser = msg.sender == "user";

                  return Column(
                    crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(14.0),
                        margin: EdgeInsets.only(
                          bottom: 12.0,
                          left: isUser ? 50.0 : 0.0,
                          right: isUser ? 0.0 : 50.0,
                        ),
                        decoration: BoxDecoration(
                          color: isUser ? AppColors.primaryGreen : Colors.white,
                          borderRadius: BorderRadius.circular(16.0),
                          border: isUser ? null : Border.all(color: AppColors.dividerColor),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 6, offset: const Offset(0, 2)),
                          ],
                        ),
                        child: Text(
                          msg.content,
                          style: TextStyle(
                            fontSize: 15,
                            color: isUser ? Colors.white : AppColors.textDark,
                            height: 1.4,
                          ),
                        ),
                      ),
                      for (var card in msg.visualCards)
                        _buildCardWidget(card as Map<String, dynamic>),
                    ],
                  );
                },
              ),
            ),
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primaryGreen)),
                    SizedBox(width: 8),
                    Text("BHOOMI is thinking...", style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  ],
                ),
              ),

            // Interactive Suggestion Chips (6 Canonical Farmer Questions)
            Container(
              height: 42,
              margin: const EdgeInsets.only(bottom: 6.0),
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16.0),
                itemCount: suggestions.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, idx) {
                  final chip = suggestions[idx];
                  return ActionChip(
                    avatar: Text(chip.icon, style: const TextStyle(fontSize: 13)),
                    label: Text(
                      chip.label,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.primaryGreen),
                    ),
                    backgroundColor: AppColors.lightGreen,
                    side: const BorderSide(color: Color(0xFFC8E6C9), width: 1.0),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                    onPressed: _isLoading ? null : () => _sendMessage(chip.query),
                  );
                },
              ),
            ),

            // Bottom Input Bar: MICROPHONE + TEXT INPUT + SEND
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10.0),
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4, offset: const Offset(0, -2)),
                ],
              ),
              child: Row(
                children: [
                  // MICROPHONE BUTTON
                  Container(
                    margin: const EdgeInsets.only(right: 8),
                    decoration: BoxDecoration(
                      color: AppColors.lightGreen,
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.primaryGreen.withOpacity(0.3)),
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.mic, color: AppColors.primaryGreen, size: 24),
                      tooltip: "Speak with Voice Assistant",
                      onPressed: _isLoading ? null : _openVoiceDialog,
                    ),
                  ),

                  // TEXT INPUT FIELD
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      decoration: InputDecoration(
                        hintText: _currentLanguage == "te"
                            ? "భూమిని ప్రశ్న అడగండి..."
                            : (_currentLanguage == "hi"
                                ? "भूमि से प्रश्न पूछें..."
                                : (_currentLanguage == "ta"
                                    ? "பூமியிடம் கேள்வி கேளுங்கள்..."
                                    : (_currentLanguage == "kn"
                                        ? "ಭೂಮಿಯನ್ನು ಪ್ರಶ್ನೆ ಕೇಳಿ..."
                                        : (_currentLanguage == "ml"
                                            ? "ഭൂമിയോട് ചോദ്യം ചോദിക്കൂ..."
                                            : "Ask BHOOMI a question...")))),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                        filled: true,
                        fillColor: AppColors.scaffoldBg,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  const SizedBox(width: 8),

                  // SEND BUTTON
                  CircleAvatar(
                    backgroundColor: AppColors.primaryGreen,
                    radius: 22,
                    child: IconButton(
                      icon: const Icon(Icons.send, color: Colors.white, size: 20),
                      tooltip: "Send Message",
                      onPressed: _isLoading ? null : () => _sendMessage(),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Voice Input Bottom Sheet for seamless speech interaction directly inside Chat
class _VoiceInputSheet extends StatefulWidget {
  final String language;
  final Function(String) onVoiceQuery;

  const _VoiceInputSheet({
    required this.language,
    required this.onVoiceQuery,
  });

  @override
  State<_VoiceInputSheet> createState() => _VoiceInputSheetState();
}

class _VoiceInputSheetState extends State<_VoiceInputSheet> {
  VoiceState _state = VoiceState.idle;

  final Map<String, List<String>> _spokenOptions = {
    "te": [
      "ఈరోజు నా పొలంలో ఏం చేయాలి?",
      "వర్షం పడుతుందా?",
      "అయితే నీరు పెట్టాలా?",
      "సరే వాయిదా వేయి.",
      "నల్లరేగడి నేలలో ఏ పంట వేయాలి?",
      "వరికి ఏ పురుగుమందు పిచికారీ చేయాలి?"
    ],
    "hi": [
      "आज मुझे खेत में क्या करना चाहिए?",
      "क्या आज बारिश होगी?",
      "क्या मुझे सिंचाई करनी चाहिए?",
      "काली मिट्टी के लिए कौन सी फसल उपयुक्त है?",
      "धान पर कौन सा कीटनाशक छिड़कें?"
    ],
    "ta": [
      "இன்று நான் என்ன செய்ய வேண்டும்?",
      "இன்று மழை பெய்யுமா?",
      "நான் பாசனம் செய்ய வேண்டுமா?",
      "நெல் பயிருக்கு என்ன மருந்து தெளிக்க வேண்டும்?"
    ],
    "kn": [
      "ಇಂದು ನಾನು ಏನು ಮಾಡಬೇಕು?",
      "ಇಂದು ಮಳೆ ಬರುತ್ತದೆಯೇ?",
      "ನಾನು ನೀರಾವರಿ ಮಾಡಬೇಕೆ?",
      "ಭತ್ತಕ್ಕೆ ಯಾವ ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸಬೇಕು?"
    ],
    "ml": [
      "ഇന്ന് ഞാൻ എന്ത് ചെയ്യണം?",
      "ഇന്ന് മഴ പെയ്യുമോ?",
      "ഞാൻ നനയ്ക്കണോ?",
      "നെല്ലിന് ഏത് കീടനാശിനി തളിക്കണം?"
    ],
    "en": [
      "What should I do today?",
      "Will it rain today?",
      "Should I irrigate?",
      "Okay postpone it.",
      "Which crop is suitable for black soil?",
      "Spray monocrotophos.",
      "What pesticide should I spray on rice?"
    ]
  };

  @override
  Widget build(BuildContext context) {
    final options = _spokenOptions[widget.language] ?? _spokenOptions["en"]!;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: 16),
          const Text("BHOOMI Voice Assistant", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark)),
          const SizedBox(height: 4),
          const Text("Speak naturally or select a quick voice query below:", style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
          const SizedBox(height: 20),
          VoiceOrb(
            state: _state,
            size: 90,
            onTap: () {
              setState(() => _state = VoiceState.listening);
            },
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: options.map((opt) {
              return ActionChip(
                avatar: const Icon(Icons.mic, size: 14, color: AppColors.primaryGreen),
                label: Text(opt, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textDark)),
                backgroundColor: AppColors.lightGreen,
                side: BorderSide(color: AppColors.primaryGreen.withOpacity(0.3)),
                onPressed: () => widget.onVoiceQuery(opt),
              );
            }).toList(),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}
