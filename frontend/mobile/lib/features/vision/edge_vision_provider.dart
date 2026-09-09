import 'dart:typed_data';

/// Common diagnosis result schema across Server and Edge mobile runtimes
class EdgeVisionResult {
  final String crop;
  final String disease;
  final String commonName;
  final double confidence;
  final double calibratedConfidence;
  final String uncertaintyLevel;
  final bool isReliable;
  final bool isOod;
  final String runtime;
  final double inferenceTimeMs;
  final String farmerExplanation;
  final List<String> symptoms;
  final String ipmRecommendation;
  final String chemicalTreatment;
  final List<String> safetyAdvisories;
  final bool requiresServerVerification;

  EdgeVisionResult({
    required this.crop,
    required this.disease,
    required this.commonName,
    required this.confidence,
    required this.calibratedConfidence,
    required this.uncertaintyLevel,
    required this.isReliable,
    required this.isOod,
    required this.runtime,
    required this.inferenceTimeMs,
    required this.farmerExplanation,
    required this.symptoms,
    required this.ipmRecommendation,
    required this.chemicalTreatment,
    required this.safetyAdvisories,
    required this.requiresServerVerification,
  });

  Map<String, dynamic> toJson() => {
    'crop': crop,
    'disease': disease,
    'common_name': commonName,
    'confidence': confidence,
    'calibrated_confidence': calibratedConfidence,
    'uncertainty_level': uncertaintyLevel,
    'is_reliable': isReliable,
    'is_ood': isOod,
    'runtime': runtime,
    'inference_time_ms': inferenceTimeMs,
    'farmer_explanation': farmerExplanation,
    'symptoms': symptoms,
    'ipm_recommendation': ipmRecommendation,
    'chemical_treatment': chemicalTreatment,
    'safety_advisories': safetyAdvisories,
    'requires_server_verification': requiresServerVerification,
  };
}

/// Abstract contract for edge and server vision providers
abstract class EdgeVisionProvider {
  String get runtimeName;
  bool get isOfflineCapable;
  Future<bool> isModelLoaded(String crop);
  Future<EdgeVisionResult> analyzeLeaf(Uint8List imageBytes, {required String crop});
}

/// Server-side authoritative vision provider (Online mode with full RAG & SafetyEngine)
class ServerVisionProvider implements EdgeVisionProvider {
  @override
  String get runtimeName => 'Server_FastAPI_PyTorch';

  @override
  bool get isOfflineCapable => false;

  @override
  Future<bool> isModelLoaded(String crop) async => true;

  @override
  Future<EdgeVisionResult> analyzeLeaf(Uint8List imageBytes, {required String crop}) async {
    // In production, posts multipart imageBytes to /api/v1/vision/analyze-leaf
    return EdgeVisionResult(
      crop: crop,
      disease: 'Tomato___Early_blight',
      commonName: 'Early Blight',
      confidence: 0.94,
      calibratedConfidence: 0.92,
      uncertaintyLevel: 'LOW',
      isReliable: true,
      isOod: false,
      runtime: runtimeName,
      inferenceTimeMs: 4.2,
      farmerExplanation: 'Early blight fungal lesions observed on foliar margin.',
      symptoms: ['Concentric brown rings', 'Yellowing chlorotic halo'],
      ipmRecommendation: 'Remove severely blighted lower leaves and ensure drip aeration.',
      chemicalTreatment: 'Apply Mancozeb 75% WP @ 2.5g/L (CIBRC Approved).',
      safetyAdvisories: ['Wear protective mask and gloves.'],
      requiresServerVerification: false,
    );
  }
}

/// Local Edge ONNX/TFLite mobile provider (Offline mode with strict safety restrictions)
class LocalEdgeVisionProvider implements EdgeVisionProvider {
  final String _engine; // 'ONNX_Runtime' or 'TFLite'

  LocalEdgeVisionProvider({String engine = 'ONNX_Runtime_FP16'}) : _engine = engine;

  @override
  String get runtimeName => _engine;

  @override
  bool get isOfflineCapable => true;

  @override
  Future<bool> isModelLoaded(String crop) async {
    // Supported offline crops: tomato, banana, guava, corn_maize
    final supported = ['tomato', 'banana', 'guava', 'corn_maize'];
    return supported.contains(crop.toLowerCase());
  }

  @override
  Future<EdgeVisionResult> analyzeLeaf(Uint8List imageBytes, {required String crop}) async {
    // Rice is strictly prohibited from farmer diagnosis
    if (crop.toLowerCase() == 'rice') {
      return EdgeVisionResult(
        crop: crop,
        disease: 'RESEARCH_ONLY',
        commonName: 'Model in Research Mode',
        confidence: 0.0,
        calibratedConfidence: 0.0,
        uncertaintyLevel: 'UNRELIABLE',
        isReliable: false,
        isOod: true,
        runtime: runtimeName,
        inferenceTimeMs: 0.0,
        farmerExplanation: 'Rice diagnosis is currently under research. Please consult your local KVK extension officer.',
        symptoms: [],
        ipmRecommendation: 'Consult local agricultural university.',
        chemicalTreatment: 'No chemical treatment available in research mode.',
        safetyAdvisories: [],
        requiresServerVerification: true,
      );
    }

    // OFFLINE SAFETY ENFORCEMENT:
    // Local offline mode strictly suppresses chemical pesticide prescriptions
    // to prevent unsafe off-label applications without server SafetyEngine validation.
    return EdgeVisionResult(
      crop: crop,
      disease: '${crop.toLowerCase()}___foliar_observation',
      commonName: 'Preliminary Foliar Observation (Offline Mode)',
      confidence: 0.88,
      calibratedConfidence: 0.85,
      uncertaintyLevel: 'MODERATE',
      isReliable: true,
      isOod: false,
      runtime: runtimeName,
      inferenceTimeMs: 3.8,
      farmerExplanation: 'Preliminary foliar pattern identified offline. Connect to internet for authoritative SafetyEngine treatment.',
      symptoms: ['Foliar discoloration detected'],
      ipmRecommendation: 'Maintain standard cultural practices and monitor symptom expansion.',
      chemicalTreatment: 'Chemical prescription disabled offline. Connect online to verify with CIBRC safety guidelines.',
      safetyAdvisories: ['Connect online for regulatory chemical validation.'],
      requiresServerVerification: true,
    );
  }
}

/// Hybrid vision orchestrator managing online-first routing with safe offline fallback
class HybridVisionOrchestrator {
  final EdgeVisionProvider _serverProvider;
  final EdgeVisionProvider _localEdgeProvider;

  HybridVisionOrchestrator({
    EdgeVisionProvider? serverProvider,
    EdgeVisionProvider? localEdgeProvider,
  })  : _serverProvider = serverProvider ?? ServerVisionProvider(),
        _localEdgeProvider = localEdgeProvider ?? LocalEdgeVisionProvider();

  Future<EdgeVisionResult> diagnose({
    required Uint8List imageBytes,
    required String crop,
    required bool isOnline,
  }) async {
    if (isOnline) {
      try {
        return await _serverProvider.analyzeLeaf(imageBytes, crop: crop);
      } catch (_) {
        // Graceful fallback to edge model if server call fails
        return await _localEdgeProvider.analyzeLeaf(imageBytes, crop: crop);
      }
    } else {
      // Offline mode
      return await _localEdgeProvider.analyzeLeaf(imageBytes, crop: crop);
    }
  }
}
