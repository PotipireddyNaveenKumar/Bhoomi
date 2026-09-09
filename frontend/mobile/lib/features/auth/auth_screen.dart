import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';
import '../../core/storage/secure_storage.dart';
import '../../routing/app_router.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({Key? key}) : super(key: key);

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool isRegister = true;
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  bool isLoading = false;
  String? errorMessage;

  Future<void> _submit() async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    final endpoint = isRegister ? ApiEndpoints.register : ApiEndpoints.login;
    final lang = await LocalStorageService.getLanguage();

    final body = isRegister
        ? {
            "phone_number": _phoneController.text.trim(),
            "password": _passwordController.text.trim(),
            "name": _nameController.text.trim(),
            "preferred_language": lang,
            "state": "Andhra Pradesh",
            "district": "Guntur",
            "village": "Tenali",
          }
        : {
            "phone_number": _phoneController.text.trim(),
            "password": _passwordController.text.trim(),
          };

    try {
      final response = await ApiClient.post(endpoint, body);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        await LocalStorageService.saveAuthData(
          token: data['access_token'],
          farmerId: data['farmer_id'],
          name: data['name'],
          language: data['preferred_language'],
        );

        if (!mounted) return;
        if (isRegister) {
          Navigator.pushReplacementNamed(context, AppRouter.onboarding);
        } else {
          Navigator.pushReplacementNamed(context, AppRouter.home);
        }
      } else {
        final err = jsonDecode(response.body);
        setState(() {
          errorMessage = err['detail'] ?? "Authentication failed.";
        });
      }
    } catch (e) {
      // Local fallback for offline/development demo
      await LocalStorageService.saveAuthData(
        token: "demo_offline_jwt_token",
        farmerId: "demo_farmer_id",
        name: _nameController.text.trim().isNotEmpty ? _nameController.text.trim() : "Farmer",
        language: lang,
      );
      if (!mounted) return;
      Navigator.pushReplacementNamed(context, AppRouter.home);
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 32),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.primaryGreen,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.eco, color: Colors.white, size: 30),
                  ),
                  const SizedBox(width: 12),
                  const Text(
                    "BHOOMI",
                    style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900, color: AppColors.textDark),
                  ),
                ],
              ),
              const SizedBox(height: 32),
              Text(
                isRegister ? "Create Farmer Profile" : "Welcome Back",
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppColors.textDark),
              ),
              const SizedBox(height: 8),
              Text(
                isRegister ? "Join your AI Farm Manager" : "Login to monitor your farm",
                style: const TextStyle(fontSize: 15, color: AppColors.textMuted),
              ),
              const SizedBox(height: 28),

              if (errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.errorRed.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: AppColors.errorRed, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(errorMessage!, style: const TextStyle(color: AppColors.errorRed, fontSize: 13)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              if (isRegister) ...[
                TextField(
                  controller: _nameController,
                  decoration: InputDecoration(
                    labelText: "Farmer Name",
                    prefixIcon: const Icon(Icons.person, color: AppColors.primaryGreen),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                ),
                const SizedBox(height: 16),
              ],

              TextField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                decoration: InputDecoration(
                  labelText: "Phone Number",
                  prefixIcon: const Icon(Icons.phone, color: AppColors.primaryGreen),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  filled: true,
                  fillColor: Colors.white,
                ),
              ),
              const SizedBox(height: 16),

              TextField(
                controller: _passwordController,
                obscureText: true,
                decoration: InputDecoration(
                  labelText: "Password",
                  prefixIcon: const Icon(Icons.lock, color: AppColors.primaryGreen),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  filled: true,
                  fillColor: Colors.white,
                ),
              ),
              const SizedBox(height: 28),

              ElevatedButton(
                onPressed: isLoading ? null : _submit,
                child: isLoading
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                      )
                    : Text(isRegister ? "Register & Continue" : "Login"),
              ),
              const SizedBox(height: 16),

              Center(
                child: TextButton(
                  onPressed: () {
                    setState(() {
                      isRegister = !isRegister;
                      errorMessage = null;
                    });
                  },
                  child: Text(
                    isRegister ? "Already have an account? Login" : "Don't have an account? Register",
                    style: const TextStyle(color: AppColors.primaryGreen, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
