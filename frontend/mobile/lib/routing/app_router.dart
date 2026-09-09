import 'package:flutter/material.dart';
import '../features/splash/splash_screen.dart';
import '../features/language/language_selection_screen.dart';
import '../features/auth/auth_screen.dart';
import '../features/onboarding/onboarding_screen.dart';
import '../features/home/home_screen.dart';
import '../features/voice/voice_assistant_screen.dart';
import '../features/chat/chat_screen.dart';
import '../features/farm/farm_profile_screen.dart';
import '../features/tasks/tasks_screen.dart';
import '../features/market/market_intelligence_screen.dart';
import '../features/profit/profit_simulator_screen.dart';
import '../features/vision/leaf_scanner_screen.dart';
import '../features/command_center/farm_command_center_screen.dart';

import '../features/weather/weather_screen.dart';

class AppRouter {
  static const String splash = '/';
  static const String languageSelect = '/language';
  static const String auth = '/auth';
  static const String onboarding = '/onboarding';
  static const String home = '/home';
  static const String voiceAssistant = '/voice';
  static const String chat = '/chat';
  static const String farmProfile = '/farm-profile';
  static const String tasks = '/tasks';
  static const String weather = '/weather';
  static const String market = '/market';
  static const String profitSimulator = '/profit-simulator';
  static const String leafScanner = '/leaf-scanner';
  static const String commandCenter = '/command-center';

  static Route<dynamic> generateRoute(RouteSettings settings, Function(Locale) onLanguageChanged) {
    switch (settings.name) {
      case splash:
        return MaterialPageRoute(builder: (_) => const SplashScreen());
      case languageSelect:
        return MaterialPageRoute(builder: (_) => LanguageSelectionScreen(onLanguageChanged: onLanguageChanged));
      case auth:
        return MaterialPageRoute(builder: (_) => const AuthScreen());
      case onboarding:
        return MaterialPageRoute(builder: (_) => OnboardingScreen(onLanguageChanged: onLanguageChanged));
      case home:
        return MaterialPageRoute(builder: (_) => HomeScreen(onLanguageChanged: onLanguageChanged));
      case voiceAssistant:
        return MaterialPageRoute(builder: (_) => const VoiceAssistantScreen());
      case chat:
        final initialQuery = settings.arguments as String?;
        return MaterialPageRoute(builder: (_) => ChatScreen(initialQuery: initialQuery));
      case farmProfile:
        return MaterialPageRoute(builder: (_) => const FarmProfileScreen());
      case tasks:
        return MaterialPageRoute(builder: (_) => const TasksScreen());
      case weather:
        return MaterialPageRoute(builder: (_) => const WeatherScreen());
      case market:
        return MaterialPageRoute(builder: (_) => const MarketIntelligenceScreen());
      case profitSimulator:
        return MaterialPageRoute(builder: (_) => const ProfitSimulatorScreen());
      case leafScanner:
        return MaterialPageRoute(builder: (_) => const LeafScannerScreen());
      case commandCenter:
        return MaterialPageRoute(builder: (_) => const FarmCommandCenterScreen());
      default:
        return MaterialPageRoute(builder: (_) => HomeScreen(onLanguageChanged: onLanguageChanged));
    }
  }
}
