import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/storage/secure_storage.dart';
import '../../routing/app_router.dart';

class LanguageSelectionScreen extends StatelessWidget {
  final Function(Locale) onLanguageChanged;

  const LanguageSelectionScreen({Key? key, required this.onLanguageChanged}) : super(key: key);

  final List<Map<String, String>> _languages = const [
    {"code": "te", "name": "తెలుగు", "englishName": "Telugu"},
    {"code": "hi", "name": "हिन्दी", "englishName": "Hindi"},
    {"code": "en", "name": "English", "englishName": "English"},
    {"code": "ta", "name": "தமிழ்", "englishName": "Tamil"},
    {"code": "kn", "name": "ಕನ್ನಡ", "englishName": "Kannada"},
    {"code": "ml", "name": "മലയാളം", "englishName": "Malayalam"},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: const Text("Choose Your Language / భాష"),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "Select preferred language for voice and farm management",
                style: TextStyle(fontSize: 16, color: AppColors.textMuted),
              ),
              const SizedBox(height: 24),
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                    childAspectRatio: 1.3,
                  ),
                  itemCount: _languages.length,
                  itemBuilder: (context, index) {
                    final lang = _languages[index];
                    return InkWell(
                      onTap: () async {
                        await LocalStorageService.setLanguage(lang['code']!);
                        onLanguageChanged(Locale(lang['code']!));
                        Navigator.pushNamed(context, AppRouter.auth);
                      },
                      borderRadius: BorderRadius.circular(16),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppColors.primaryGreen.withOpacity(0.3), width: 1.5),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.04),
                              blurRadius: 8,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              lang['name']!,
                              style: const TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.bold,
                                color: AppColors.textDark,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              lang['englishName']!,
                              style: const TextStyle(
                                fontSize: 14,
                                color: AppColors.textMuted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
