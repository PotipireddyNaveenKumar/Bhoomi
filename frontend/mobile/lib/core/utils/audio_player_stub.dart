import 'package:flutter/foundation.dart';

typedef AudioErrorCallback = void Function(String error);

void playBase64Audio(
  String base64Audio, {
  String mimeType = "audio/wav",
  VoidCallback? onStarted,
  VoidCallback? onEnded,
  AudioErrorCallback? onError,
  VoidCallback? onAutoplayBlocked,
}) {
  // Non-web stub
}

void resumeActiveAudio({VoidCallback? onStarted, VoidCallback? onEnded}) {
  // Non-web stub
}

void stopAudio() {
  // Non-web stub
}
