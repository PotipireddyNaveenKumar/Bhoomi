import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'core/theme/app_theme.dart';
import 'core/storage/secure_storage.dart';
import 'localization/app_localizations.dart';
import 'routing/app_router.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final savedLanguage = await LocalStorageService.getLanguage();
  runApp(BhoomiApp(initialLocale: Locale(savedLanguage)));
}

class BhoomiApp extends StatefulWidget {
  final Locale initialLocale;
  const BhoomiApp({Key? key, required this.initialLocale}) : super(key: key);

  @override
  State<BhoomiApp> createState() => _BhoomiAppState();
}

class _BhoomiAppState extends State<BhoomiApp> {
  late Locale _locale;

  @override
  void initState() {
    super.initState();
    _locale = widget.initialLocale;
  }

  void _setLocale(Locale locale) {
    setState(() {
      _locale = locale;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BHOOMI V2 — Personal AI Farm Manager',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      locale: _locale,
      supportedLocales: const [
        Locale('en', ''), // English
        Locale('te', ''), // Telugu
        Locale('hi', ''), // Hindi
        Locale('ta', ''), // Tamil
        Locale('kn', ''), // Kannada
        Locale('ml', ''), // Malayalam
      ],
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      initialRoute: AppRouter.splash,
      onGenerateRoute: (settings) => AppRouter.generateRoute(settings, _setLocale),
    );
  }
}
