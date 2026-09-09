import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/constants/app_colors.dart';
import '../../core/networking/api_client.dart';
import '../../core/utils/file_picker_helper.dart';
import '../../shared/cards/leaf_diagnosis_card.dart';
import '../../routing/app_router.dart';

class LeafScannerScreen extends StatefulWidget {
  const LeafScannerScreen({super.key});

  @override
  State<LeafScannerScreen> createState() => _LeafScannerScreenState();
}

class _LeafScannerScreenState extends State<LeafScannerScreen> {
  bool _isAnalyzing = false;
  Uint8List? _selectedImageBytes;
  String? _selectedFilename;
  String _selectedCrop = "Chilli";
  Map<String, dynamic>? _diagnosisResult;
  String? _errorMessage;
  @override
  void initState() {
    super.initState();
  }

  void _pickFromDevice() {
    pickImageFile((bytes, filename) {
      setState(() {
        _selectedImageBytes = Uint8List.fromList(bytes);
        _selectedFilename = filename;
        _diagnosisResult = null;
        _errorMessage = null;
      });
    });
  }

  Future<void> _analyzeLeaf() async {
    if (_selectedImageBytes == null) {
      setState(() {
        _errorMessage = "Please upload or select a leaf photo first.";
      });
      return;
    }

    setState(() {
      _isAnalyzing = true;
      _errorMessage = null;
      _diagnosisResult = null;
    });

    try {
      final response = await ApiClient.postMultipart(
        ApiEndpoints.visionAnalyze,
        fileBytes: _selectedImageBytes!,
        filename: _selectedFilename ?? "leaf.jpg",
        fields: {"crop_hint": _selectedCrop.toLowerCase()},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _isAnalyzing = false;
          _diagnosisResult = data;
        });
      } else {
        final err = jsonDecode(response.body);
        setState(() {
          _isAnalyzing = false;
          _errorMessage = err["detail"] ?? "Diagnostic analysis failed (HTTP ${response.statusCode})";
        });
      }
    } catch (e) {
      setState(() {
        _isAnalyzing = false;
        _errorMessage = "Failed to connect to Vision Pathology Service: $e";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Plant Pathology Scanner"),
        backgroundColor: AppColors.primaryGreen,
        foregroundColor: Colors.white,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 860),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header & Crop selector
                Card(
                  elevation: 2,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Row(
                      children: [
                        const Icon(Icons.eco_rounded, color: AppColors.primaryGreen, size: 28),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                "Computer Vision Leaf Diagnostics",
                                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                              ),
                              Text(
                                "Multi-crop pathology, quality gate & SafetyEngine verification",
                                style: TextStyle(fontSize: 12, color: Colors.grey),
                              ),
                            ],
                          ),
                        ),
                        DropdownButton<String>(
                          value: _selectedCrop,
                          underline: Container(height: 2, color: AppColors.primaryGreen),
                          items: const [
                            DropdownMenuItem(value: "Chilli", child: Text("Chilli (Teja)")),
                            DropdownMenuItem(value: "Rice", child: Text("Rice / Paddy (RESEARCH_ONLY)")),
                            DropdownMenuItem(value: "Tomato", child: Text("Tomato")),
                          ],
                          onChanged: (val) {
                            if (val != null) {
                              setState(() {
                                _selectedCrop = val;
                              });
                            }
                          },
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // Image Preview Frame
                Container(
                  height: 280,
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.grey[300]!, width: 2),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(14),
                    child: _selectedImageBytes != null
                        ? Stack(
                            fit: StackFit.expand,
                            children: [
                              Image.memory(
                                _selectedImageBytes!,
                                fit: BoxFit.contain,
                              ),
                              Positioned(
                                top: 8,
                                right: 8,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withOpacity(0.65),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text(
                                    _selectedFilename ?? "Leaf Image",
                                    style: const TextStyle(color: Colors.white, fontSize: 12),
                                  ),
                                ),
                              ),
                              if (_isAnalyzing)
                                Container(
                                  color: Colors.black.withOpacity(0.4),
                                  child: const Center(
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        CircularProgressIndicator(color: Colors.white),
                                        SizedBox(height: 12),
                                        Text(
                                          "Validating Quality Gate & Diagnosing...",
                                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                            ],
                          )
                        : Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.photo_library_outlined, size: 64, color: Colors.grey[400]),
                                const SizedBox(height: 12),
                                Text(
                                  "Tap 'Capture Photo' or 'Gallery' to upload a crop leaf image for pathology analysis",
                                  textAlign: TextAlign.center,
                                  style: TextStyle(color: Colors.grey[600], fontSize: 14),
                                ),
                              ],
                            ),
                          ),
                  ),
                ),
                const SizedBox(height: 16),

                // Action Buttons
                Row(
                  children: [
                    Expanded(
                      flex: 2,
                      child: ElevatedButton.icon(
                        onPressed: _isAnalyzing ? null : _analyzeLeaf,
                        icon: const Icon(Icons.camera_alt_rounded),
                        label: Text(_isAnalyzing ? "Analyzing..." : "Capture Photo"),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primaryGreen,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 1,
                      child: OutlinedButton.icon(
                        onPressed: _isAnalyzing ? null : _pickFromDevice,
                        icon: const Icon(Icons.photo_library_rounded),
                        label: const Text("Gallery"),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.primaryGreen,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                    ),
                  ],
                ),

                // Error Message
                if (_errorMessage != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline_rounded, color: Colors.red),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(_errorMessage!, style: const TextStyle(color: Colors.red, fontSize: 13)),
                        ),
                      ],
                    ),
                  ),
                ],

                // Diagnosis Result Card
                if (_diagnosisResult != null) ...[
                  const SizedBox(height: 20),
                  LeafDiagnosisCard(data: _diagnosisResult!),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.primaryGreen.withOpacity(0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          "Next Recommended Actions",
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppColors.textDark),
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          icon: const Icon(Icons.add_task_rounded, size: 18),
                          label: const Text("Add Crop Inspection Task"),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primaryGreen,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          onPressed: () async {
                            try {
                              await ApiClient.post(ApiEndpoints.tasks, {
                                "title": "Field Inspection: ${_selectedCrop} (${_diagnosisResult!['disease_name'] ?? 'Leaf Condition'})",
                                "task_type": "FIELD_INSPECTION",
                                "crop": _selectedCrop,
                                "priority": "high",
                                "due_at": DateTime.now().add(const Duration(days: 1)).toIso8601String().split('T')[0],
                                "reason": "Follow-up inspection based on vision scan diagnosis: ${_diagnosisResult!['disease_name'] ?? 'Leaf Condition'}",
                              });
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text("Field Inspection task added to your farm schedule!"),
                                    backgroundColor: AppColors.primaryGreen,
                                  ),
                                );
                              }
                            } catch (e) {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text("Could not add task: $e"), backgroundColor: Colors.red),
                                );
                              }
                            }
                          },
                        ),
                        const SizedBox(height: 10),
                        OutlinedButton.icon(
                          icon: const Icon(Icons.chat_bubble_outline_rounded, size: 18),
                          label: const Text("Ask BHOOMI: How to manage this condition?"),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppColors.primaryGreen,
                            side: const BorderSide(color: AppColors.primaryGreen),
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          onPressed: () {
                            final disease = _diagnosisResult!['disease_name'] ?? 'leaf symptoms';
                            final query = "My $_selectedCrop has $disease. How do I manage this condition?";
                            Navigator.pushNamed(context, AppRouter.chat, arguments: query);
                          },
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
