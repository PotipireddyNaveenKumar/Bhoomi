// ignore: avoid_web_libraries_in_flutter
import 'dart:convert';
import 'dart:html' as html;
import 'package:flutter/foundation.dart';

html.AudioElement? _activeAudio;
String? _activeObjectUrl;

typedef AudioErrorCallback = void Function(String error);

void playBase64Audio(
  String base64Audio, {
  String mimeType = "audio/wav",
  VoidCallback? onStarted,
  VoidCallback? onEnded,
  AudioErrorCallback? onError,
  VoidCallback? onAutoplayBlocked,
}) {
  try {
    stopAudio();

    final bytes = base64Decode(base64Audio);
    final blob = html.Blob([bytes], mimeType);
    final url = html.Url.createObjectUrlFromBlob(blob);
    _activeObjectUrl = url;

    final audio = html.AudioElement(url);
    _activeAudio = audio;

    audio.onPlay.listen((_) {
      onStarted?.call();
    });

    audio.onEnded.listen((_) {
      onEnded?.call();
      _cleanup();
    });

    audio.onError.listen((e) {
      onError?.call("Audio playback error occurred");
      _cleanup();
    });

    audio.play().then((_) {
      onStarted?.call();
    }).catchError((error) {
      debugPrint("Audio autoplay blocked by browser: $error");
      onAutoplayBlocked?.call();
    });
  } catch (e) {
    debugPrint("Failed to initialize audio: $e");
    onError?.call(e.toString());
    _cleanup();
  }
}

void resumeActiveAudio({VoidCallback? onStarted, VoidCallback? onEnded}) {
  if (_activeAudio != null) {
    _activeAudio!.play().then((_) {
      onStarted?.call();
    }).catchError((err) {
      debugPrint("Resume failed: $err");
    });
  }
}

void stopAudio() {
  if (_activeAudio != null) {
    try {
      _activeAudio!.pause();
      _activeAudio!.currentTime = 0;
    } catch (_) {}
    _cleanup();
  }
}

void _cleanup() {
  if (_activeObjectUrl != null) {
    try {
      html.Url.revokeObjectUrl(_activeObjectUrl!);
    } catch (_) {}
    _activeObjectUrl = null;
  }
  _activeAudio = null;
}
