import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class TaskCard extends StatelessWidget {
  final String title;
  final String? subtitle;
  final String dueDate;
  final String priority;
  final bool isCompleted;
  final VoidCallback? onToggle;

  const TaskCard({
    Key? key,
    required this.title,
    this.subtitle,
    required this.dueDate,
    this.priority = "medium",
    this.isCompleted = false,
    this.onToggle,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    Color getPriorityColor() {
      if (priority == "high" || priority == "urgent") return AppColors.errorRed;
      if (priority == "medium") return AppColors.warningOrange;
      return AppColors.primaryGreen;
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6.0),
      padding: const EdgeInsets.all(14.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14.0),
        border: Border.all(color: AppColors.dividerColor),
      ),
      child: Row(
        children: [
          IconButton(
            icon: Icon(
              isCompleted ? Icons.check_circle : Icons.radio_button_unchecked,
              color: isCompleted ? AppColors.primaryGreen : AppColors.textMuted,
              size: 26,
            ),
            onPressed: onToggle,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: isCompleted ? AppColors.textMuted : AppColors.textDark,
                    decoration: isCompleted ? TextDecoration.lineThrough : null,
                  ),
                ),
                if (subtitle != null && subtitle!.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(subtitle!, style: const TextStyle(fontSize: 13, color: AppColors.textMuted)),
                ],
                const SizedBox(height: 6),
                Row(
                  children: [
                    Icon(Icons.calendar_today, size: 12, color: AppColors.textMuted),
                    const SizedBox(width: 4),
                    Text(dueDate, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                    const SizedBox(width: 12),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: getPriorityColor().withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        priority.toUpperCase(),
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: getPriorityColor()),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
