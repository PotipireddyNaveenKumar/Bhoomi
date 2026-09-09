import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/utils/audio_player_helper.dart';
import '../../shared/widgets/voice_orb.dart';
import '../../shared/cards/weather_card.dart';
import '../../shared/cards/market_card.dart';
import '../../shared/cards/profit_card.dart';
import '../../shared/cards/simulation_card.dart';
import '../../shared/cards/risk_card.dart';

class VoiceAssistantScreen extends StatefulWidget {
  const VoiceAssistantScreen({Key? key}) : super(key: key);

  @override
  State<VoiceAssistantScreen> createState() => _VoiceAssistantScreenState();
}

class _VoiceAssistantScreenState extends State<VoiceAssistantScreen> {
  VoiceState _state = VoiceState.idle;
  String _userTranscript = "";
  String _assistantResponse = "";
  String _errorMessage = "";
  String _activeLanguage = "en";
  bool _isPlayingAudio = false;
  bool _autoplayBlocked = false;
  String? _cachedAudioBase64;
  List<dynamic> _visualCards = [];

  List<Map<String, String>> get _currentSuggestions {
    switch (_activeLanguage) {
      case "te":
        return const [
          {"label": "ఈరోజు ఏం చేయాలి?", "query": "ఈరోజు నా పొలంలో ఏం చేయాలి?", "lang": "te"},
          {"label": "వర్షం పడుతుందా?", "query": "ఈరోజు వర్షం పడుతుందా?", "lang": "te"},
          {"label": "నీరు పెట్టాలా?", "query": "ఈరోజు నా మిర్చి పంటకు నీరు పెట్టాలా?", "lang": "te"},
          {"label": "మార్కెట్ ధర ఎంత?", "query": "ఈరోజు గుంటూరు మిర్చి మార్కెట్ ధర ఎంత?", "lang": "te"},
        ];
      case "hi":
        return const [
          {"label": "आज क्या करना चाहिए?", "query": "आज मुझे खेत में क्या करना चाहिए?", "lang": "hi"},
          {"label": "क्या बारिश होगी?", "query": "क्या आज बारिश होगी?", "lang": "hi"},
          {"label": "क्या सिंचाई करें?", "query": "क्या मुझे आज खेत में सिंचाई करनी चाहिए?", "lang": "hi"},
          {"label": "मिर्च का भाव?", "query": "आज मिर्च का मंडी भाव क्या है?", "lang": "hi"},
        ];
      case "ta":
        return const [
          {"label": "இன்று என்ன செய்ய வேண்டும்?", "query": "இன்று என் வயலில் என்ன செய்ய வேண்டும்?", "lang": "ta"},
          {"label": "மழை பெய்யுமா?", "query": "இன்று மழை பெய்யுமா?", "lang": "ta"},
          {"label": "பாசனம் செய்ய வேண்டுமா?", "query": "இன்று பாசனம் செய்ய வேண்டுமா?", "lang": "ta"},
        ];
      case "kn":
        return const [
          {"label": "ಇಂದು ಏನು ಮಾಡಬೇಕು?", "query": "ಇಂದು ನನ್ನ ಹೊಲದಲ್ಲಿ ಏನು ಮಾಡಬೇಕು?", "lang": "kn"},
          {"label": "ಮಳೆ ಬರುತ್ತದೆಯೇ?", "query": "ಇಂದು ಮಳೆ ಬರುತ್ತದೆಯೇ?", "lang": "kn"},
          {"label": "ನೀರಾವರಿ ಮಾಡಬೇಕೆ?", "query": "ಇಂದು ನೀರಾವರಿ ಮಾಡಬೇಕೆ?", "lang": "kn"},
        ];
      default:
        return const [
          {"label": "What should I do today?", "query": "What should I do today?", "lang": "en"},
          {"label": "Will it rain today?", "query": "Will it rain today?", "lang": "en"},
          {"label": "Should I irrigate today?", "query": "Should I irrigate today?", "lang": "en"},
          {"label": "Chilli market price?", "query": "What is today's chilli market price?", "lang": "en"},
          {"label": "Postpone spraying 2 days", "query": "Postpone spraying by two days.", "lang": "en"},
        ];
    }
  }

  @override
  void initState() {
    super.initState();
    _loadLanguage();
  }

  @override
  void dispose() {
    stopAudio();
    super.dispose();
  }

  Future<void> _loadLanguage() async {
    final lang = await LocalStorageService.getLanguage();
    setState(() => _activeLanguage = lang);
  }

  Future<void> _processVoiceQuery(String queryText, [String? langCode]) async {
    final targetLang = langCode ?? _activeLanguage;
    final farmerId = await LocalStorageService.getFarmerId();

    setState(() {
      _state = VoiceState.listening;
      _userTranscript = queryText;
      _assistantResponse = "";
      _errorMessage = "";
      _visualCards = [];
      _autoplayBlocked = false;
      _cachedAudioBase64 = null;
    });

    await Future.delayed(const Duration(milliseconds: 400));
    if (!mounted) return;

    setState(() => _state = VoiceState.processing);

    await Future.delayed(const Duration(milliseconds: 300));
    if (!mounted) return;

    setState(() => _state = VoiceState.thinking);

    try {
      // 1. Send query to unified voice / decision endpoint
      final payload = {
        "text": queryText,
        "language": targetLang,
        "conversation_id": "session_voice_${DateTime.now().millisecondsSinceEpoch}",
      };
      if (farmerId != null && farmerId.isNotEmpty) {
        payload["farmer_id"] = farmerId;
      }

      final response = await ApiClient.post("${ApiEndpoints.baseUrl}/voice/task-action", payload);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final responseText = data['response_text'] ?? "";

        setState(() {
          _assistantResponse = responseText;
          _state = VoiceState.responding;
        });

        // 2. Synthesize audio with Sarvam TTS
        _synthesizeAndPlaySpeech(responseText, targetLang);
      } else {
        // Fallback to chat endpoint if task-action returned non-200
        final chatRes = await ApiClient.post(ApiEndpoints.chat, {
          "message": queryText,
          "language": targetLang,
          "input_mode": "voice"
        });

        if (chatRes.statusCode == 200) {
          final data = jsonDecode(chatRes.body);
          final responseText = data['response'] ?? "";
          setState(() {
            _assistantResponse = responseText;
            _visualCards = data['visual_cards'] ?? [];
            _state = VoiceState.responding;
          });
          _synthesizeAndPlaySpeech(responseText, targetLang);
        } else {
          throw Exception("API Error: HTTP ${chatRes.statusCode}");
        }
      }
    } catch (e) {
      setState(() {
        _state = VoiceState.error;
        _errorMessage = "Voice service error: $e";
      });
    }
  }

  Future<void> _synthesizeAndPlaySpeech(String text, String lang) async {
    try {
      setState(() {
        _isPlayingAudio = false;
        _autoplayBlocked = false;
        _cachedAudioBase64 = null;
      });

      final synthRes = await ApiClient.post("${ApiEndpoints.baseUrl}/voice/synthesize", {
        "text": text.replaceAll("**", ""),
        "language_code": lang,
      });

      if (synthRes.statusCode == 200) {
        final data = jsonDecode(synthRes.body);
        final b64Audio = data['audio_base64'];
        if (b64Audio != null && b64Audio.toString().isNotEmpty) {
          final audioStr = b64Audio.toString();
          if (mounted) {
            setState(() {
              _cachedAudioBase64 = audioStr;
            });
          }
          playBase64Audio(
            audioStr,
            onStarted: () {
              if (mounted) {
                setState(() {
                  _isPlayingAudio = true;
                  _autoplayBlocked = false;
                });
              }
            },
            onEnded: () {
              if (mounted) {
                setState(() {
                  _isPlayingAudio = false;
                });
              }
            },
            onError: (err) {
              if (mounted) {
                setState(() {
                  _isPlayingAudio = false;
                });
              }
            },
            onAutoplayBlocked: () {
              if (mounted) {
                setState(() {
                  _isPlayingAudio = false;
                  _autoplayBlocked = true;
                });
              }
            },
          );
        }
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isPlayingAudio = false;
        });
      }
    }
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
      case 'safety_restriction_card':
        return Container(
          margin: const EdgeInsets.symmetric(vertical: 8.0),
          padding: const EdgeInsets.all(16.0),
          decoration: BoxDecoration(
            color: Colors.red.shade50,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.red.shade400, width: 2),
          ),
          child: Row(
            children: [
              const Icon(Icons.shield_rounded, color: Colors.red, size: 32),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      card['title'] ?? "Safety Perimeter Blocked",
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.red),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      "Prohibited / unvetted chemical intervention was intercepted and blocked by SafetyEngine.",
                      style: TextStyle(fontSize: 12, color: Colors.black87),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }

  String _getStateStatusLabel() {
    switch (_state) {
      case VoiceState.idle:
        return "Tap microphone to speak with BHOOMI";
      case VoiceState.listening:
        return "Listening to farmer's voice input...";
      case VoiceState.processing:
        return "Processing speech & detecting language (Sarvam STT)...";
      case VoiceState.thinking:
        return "Checking Farm Digital Twin & running Decision Intelligence...";
      case VoiceState.responding:
        return _isPlayingAudio
            ? "BHOOMI is speaking (Sarvam Bulbul TTS)..."
            : "BHOOMI Farm Manager Response:";
      case VoiceState.error:
        return "Voice Diagnostic Error";
      case VoiceState.offline:
        return "Voice Service Offline — Using Local Farm Intelligence";
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: const Text("BHOOMI Voice Assistant"),
        backgroundColor: AppColors.primaryGreen,
        foregroundColor: Colors.white,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 860),
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
            child: Column(
              children: [
                // Sarvam Voice Engine Status Badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.primaryGreen.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppColors.primaryGreen.withOpacity(0.3)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.mic, color: AppColors.primaryGreen, size: 16),
                      SizedBox(width: 6),
                      Text(
                        "SARVAM AI VOICE ENGINE (Saaras STT & Bulbul TTS)",
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.primaryGreen),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Large Central Voice Orb
                VoiceOrb(
                  state: _state,
                  onTap: () => _processVoiceQuery("What should I do today?", _activeLanguage),
                  size: 130,
                ),
                const SizedBox(height: 16),

                // State Status Label
                Text(
                  _getStateStatusLabel(),
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: _state == VoiceState.error ? Colors.red : AppColors.textDark,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 20),

                // Farmer Suggested Voice Inquiries
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    _activeLanguage == "te"
                        ? "సూచించిన ప్రశ్నలు (వినడానికి తాకండి):"
                        : (_activeLanguage == "hi"
                            ? "सुझाए गए प्रश्न (बोलने के लिए टैप करें):"
                            : "Suggested Questions (Tap to speak):"),
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.black87),
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _currentSuggestions.map((s) {
                    return ActionChip(
                      avatar: const Icon(Icons.record_voice_over_rounded, size: 16, color: AppColors.primaryGreen),
                      label: Text(s["label"]!, style: const TextStyle(fontSize: 12)),
                      backgroundColor: Colors.white,
                      side: BorderSide(color: AppColors.primaryGreen.withOpacity(0.3)),
                      onPressed: _state == VoiceState.thinking || _state == VoiceState.processing
                          ? null
                          : () => _processVoiceQuery(s["query"]!, s["lang"]!),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 24),

                // User Transcript Display
                if (_userTranscript.isNotEmpty) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14.0),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(12.0),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.person, size: 20, color: Colors.grey),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            "\"$_userTranscript\"",
                            style: const TextStyle(fontSize: 15, fontStyle: FontStyle.italic),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Assistant Response Display
                if (_assistantResponse.isNotEmpty) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(18.0),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16.0),
                      border: Border.all(color: AppColors.primaryGreen.withOpacity(0.4), width: 1.5),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 3)),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.eco, color: AppColors.primaryGreen, size: 20),
                            const SizedBox(width: 8),
                            const Text(
                              "BHOOMI AI FARM MANAGER",
                              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.primaryGreen),
                            ),
                            const Spacer(),
                            if (_isPlayingAudio)
                              InkWell(
                                onTap: () {
                                  stopAudio();
                                  setState(() => _isPlayingAudio = false);
                                },
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppColors.primaryGreen.withOpacity(0.12),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.volume_up_rounded, size: 16, color: AppColors.primaryGreen),
                                      SizedBox(width: 4),
                                      Text("Speaking... (Tap to Stop)", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.primaryGreen)),
                                    ],
                                  ),
                                ),
                              )
                            else if (_cachedAudioBase64 != null)
                              ElevatedButton.icon(
                                onPressed: () {
                                  playBase64Audio(
                                    _cachedAudioBase64!,
                                    onStarted: () {
                                      if (mounted) setState(() { _isPlayingAudio = true; _autoplayBlocked = false; });
                                    },
                                    onEnded: () {
                                      if (mounted) setState(() => _isPlayingAudio = false);
                                    },
                                    onError: (_) {
                                      if (mounted) setState(() => _isPlayingAudio = false);
                                    },
                                  );
                                },
                                icon: const Icon(Icons.play_arrow_rounded, size: 16),
                                label: Text(_autoplayBlocked
                                    ? (_activeLanguage == "te" ? "వినడానికి తాకండి (Play Audio)" : "Tap to Listen")
                                    : (_activeLanguage == "te" ? "మళ్ళీ వినండి" : "Replay Audio")),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppColors.primaryGreen,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                  textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                ),
                              ),
                          ],
                        ),
                        const Divider(height: 20),
                        Text(
                          _assistantResponse,
                          style: const TextStyle(fontSize: 15, height: 1.45, color: AppColors.textDark),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Error Message Display
                if (_errorMessage.isNotEmpty) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14.0),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(12.0),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, color: Colors.red),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(_errorMessage, style: const TextStyle(color: Colors.red, fontSize: 13)),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Visual Cards Display
                if (_visualCards.isNotEmpty) ...[
                  for (var card in _visualCards) ...[
                    _buildCardWidget(card as Map<String, dynamic>),
                    const SizedBox(height: 12),
                  ],
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
