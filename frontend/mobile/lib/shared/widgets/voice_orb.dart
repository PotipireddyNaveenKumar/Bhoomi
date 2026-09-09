import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

enum VoiceState { idle, listening, processing, thinking, responding, error, offline }

class VoiceOrb extends StatefulWidget {
  final VoiceState state;
  final VoidCallback onTap;
  final double size;

  const VoiceOrb({
    Key? key,
    required this.state,
    required this.onTap,
    this.size = 140.0,
  }) : super(key: key);

  @override
  State<VoiceOrb> createState() => _VoiceOrbState();
}

class _VoiceOrbState extends State<VoiceOrb> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color _getStateColor() {
    switch (widget.state) {
      case VoiceState.idle:
        return AppColors.primaryGreen;
      case VoiceState.listening:
        return AppColors.accentGold;
      case VoiceState.processing:
      case VoiceState.thinking:
        return AppColors.skyBlue;
      case VoiceState.responding:
        return AppColors.deepGreen;
      case VoiceState.error:
        return AppColors.errorRed;
      case VoiceState.offline:
        return Colors.blueGrey;
    }
  }

  IconData _getStateIcon() {
    switch (widget.state) {
      case VoiceState.idle:
        return Icons.mic;
      case VoiceState.listening:
        return Icons.graphic_eq;
      case VoiceState.processing:
        return Icons.sync;
      case VoiceState.thinking:
        return Icons.psychology;
      case VoiceState.responding:
        return Icons.volume_up;
      case VoiceState.error:
        return Icons.error_outline;
      case VoiceState.offline:
        return Icons.cloud_off;
    }
  }

  String _getStateText() {
    switch (widget.state) {
      case VoiceState.idle:
        return "TAP AND SPEAK";
      case VoiceState.listening:
        return "Listening...";
      case VoiceState.processing:
        return "Processing speech...";
      case VoiceState.thinking:
        return "Checking farm data...";
      case VoiceState.responding:
        return "Responding...";
      case VoiceState.error:
        return "Tap to retry";
      case VoiceState.offline:
        return "Voice Offline";
    }
  }

  @override
  Widget build(BuildContext context) {
    final activeColor = _getStateColor();
    final isAnimating = widget.state != VoiceState.idle;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: widget.onTap,
          child: AnimatedBuilder(
            animation: _scaleAnimation,
            builder: (context, child) {
              return Transform.scale(
                scale: isAnimating ? _scaleAnimation.value : 1.0,
                child: Container(
                  width: widget.size,
                  height: widget.size,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        activeColor.withOpacity(0.85),
                        activeColor,
                        activeColor.withOpacity(0.95),
                      ],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: activeColor.withOpacity(0.4),
                        blurRadius: isAnimating ? 28 : 14,
                        spreadRadius: isAnimating ? 6 : 2,
                      ),
                    ],
                  ),
                  child: Center(
                    child: Icon(
                      _getStateIcon(),
                      color: Colors.white,
                      size: widget.size * 0.45,
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 16),
        Text(
          _getStateText(),
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: activeColor,
            letterSpacing: 0.2,
          ),
        ),
      ],
    );
  }
}
