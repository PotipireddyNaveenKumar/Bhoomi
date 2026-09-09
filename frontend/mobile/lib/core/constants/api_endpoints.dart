class ApiEndpoints {
  // Configurable base URL (passed via --dart-define=API_BASE_URL=... at build time)
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8085/api/v1',
  );

  // Auth
  static const String register = "$baseUrl/auth/register";
  static const String login = "$baseUrl/auth/login";

  // Farmer & Farm
  static const String farmerProfile = "$baseUrl/farmer";
  static const String farms = "$baseUrl/farms";

  // Chat & Voice
  static const String chat = "$baseUrl/chat";
  static const String chatSessions = "$baseUrl/chat/sessions";
  static const String voiceTranscribe = "$baseUrl/voice/transcribe";
  static const String voiceSynthesize = "$baseUrl/voice/synthesize";
  static const String voiceInteract = "$baseUrl/voice/interact";

  // Intelligence
  static const String weather = "$baseUrl/weather";
  static const String market = "$baseUrl/market";
  static const String profitCalculate = "$baseUrl/profit/calculate";
  static const String simulationRun = "$baseUrl/simulation/run";
  static const String riskAssess = "$baseUrl/risk/assess";
  static const String tasks = "$baseUrl/tasks";
  static const String imageAnalyze = "$baseUrl/image/analyze";

  // Phase 2 ML & Decision Intelligence
  static const String mlCropRecommendation = "$baseUrl/ml/crop-recommendation";
  static const String mlYieldPrediction = "$baseUrl/ml/yield-prediction";
  static const String mlFertilizerRecommendation = "$baseUrl/ml/fertilizer-recommendation";
  static const String visionAnalyze = "$baseUrl/vision/analyze";
  static const String ragSearch = "$baseUrl/rag/search";
  static const String farmSummary = "$baseUrl/farm/summary";
  static const String farmCrops = "$baseUrl/farm/crops";
  static const String compareCrops = "$baseUrl/farm/compare-crops";

  // Phase 3 Personal AI Farm Manager
  static const String managerState = "$baseUrl/manager/state";
  static const String managerBriefingToday = "$baseUrl/manager/briefing/today";
  static const String managerBriefingWeek = "$baseUrl/manager/briefing/week";
  static const String managerChanges = "$baseUrl/manager/changes";
  static const String managerAlerts = "$baseUrl/manager/alerts";
  static const String managerEvents = "$baseUrl/manager/events";
  static const String managerTimeline = "$baseUrl/manager/timeline";
  static const String managerPlan = "$baseUrl/manager/plan";
}
