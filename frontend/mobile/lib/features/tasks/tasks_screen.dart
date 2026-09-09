import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/networking/api_client.dart';
import '../../core/storage/secure_storage.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({Key? key}) : super(key: key);

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  List<Map<String, dynamic>> _todayTasks = [];
  List<Map<String, dynamic>> _weekTasks = [];
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadTasks();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadTasks() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final farmerId = await LocalStorageService.getFarmerId();
      final queryParam = (farmerId != null && farmerId.isNotEmpty) ? "?farmer_id=${Uri.encodeComponent(farmerId)}" : "";

      final todayRes = await ApiClient.get("${ApiEndpoints.tasks}/today$queryParam");
      if (todayRes.statusCode == 200) {
        final List<dynamic> todayList = jsonDecode(todayRes.body);
        _todayTasks = todayList.map((e) => Map<String, dynamic>.from(e)).toList();
      }

      final weekRes = await ApiClient.get("${ApiEndpoints.tasks}/week$queryParam");
      if (weekRes.statusCode == 200) {
        final List<dynamic> weekList = jsonDecode(weekRes.body);
        _weekTasks = weekList.map((e) => Map<String, dynamic>.from(e)).toList();
      }
    } catch (e) {
      _errorMessage = "Failed to load live tasks from backend: $e";
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _completeTask(String taskId) async {
    try {
      final farmerId = await LocalStorageService.getFarmerId() ?? "farmer_demo_1";
      final res = await ApiClient.post("${ApiEndpoints.tasks}/$taskId/complete", {
        "farmer_id": farmerId,
        "farm_id": "farm_1",
        "completion_source": "APP"
      });
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Task marked COMPLETED!"), backgroundColor: AppColors.primaryGreen),
        );
        _loadTasks();
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed: $e"), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _postponeTask(String taskId) async {
    try {
      final farmerId = await LocalStorageService.getFarmerId() ?? "farmer_demo_1";
      final res = await ApiClient.post("${ApiEndpoints.tasks}/$taskId/postpone", {
        "farmer_id": farmerId,
        "farm_id": "farm_1",
        "days_to_postpone": 2,
        "reason": "Postponed by 2 days via Tasks screen"
      });
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Task postponed by 2 days (+05:30 timezone preserved)."), backgroundColor: Colors.blue),
        );
        _loadTasks();
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed: $e"), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _skipTaskWithConfirmation(Map<String, dynamic> task) async {
    final title = task['title'] ?? 'Task';
    final taskId = task['task_id'] ?? '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.orange),
            SizedBox(width: 8),
            Text("Confirm Task Skip"),
          ],
        ),
        content: Text(
          "Skipping '$title' may impact crop development because soil moisture is low and rain is uncertain.\n\nDo you still want to skip this task?",
          style: const TextStyle(fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text("NO, CANCEL"),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text("YES, SKIP"),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        final farmerId = await LocalStorageService.getFarmerId() ?? "farmer_demo_1";
        final res = await ApiClient.post("${ApiEndpoints.tasks}/$taskId/skip", {
          "farmer_id": farmerId,
          "farm_id": "farm_1",
          "reason": "Farmer confirmed skip on Tasks screen"
        });
        if (res.statusCode == 200) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Task skipped as requested."), backgroundColor: Colors.orange),
          );
          _loadTasks();
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Skip failed: $e"), backgroundColor: Colors.red),
        );
      }
    }
  }

  Widget _buildTaskList(List<Map<String, dynamic>> tasks) {
    if (tasks.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle_outline, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 12),
            const Text("No pending tasks! Your farm is up to date.", style: TextStyle(color: Colors.grey, fontSize: 16)),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16.0),
      itemCount: tasks.length,
      itemBuilder: (context, index) {
        final t = tasks[index];
        final taskId = t['task_id'] ?? '';
        final status = (t['status'] ?? '').toString().toUpperCase();
        final isCompleted = status == 'COMPLETED';
        final priority = (t['priority'] ?? 'medium').toString().toLowerCase();

        Color priorityColor = AppColors.primaryGreen;
        if (priority == 'high' || priority == 'urgent') priorityColor = Colors.red;
        if (priority == 'medium') priorityColor = Colors.orange;

        return Card(
          margin: const EdgeInsets.only(bottom: 12.0),
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14.0)),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    IconButton(
                      icon: Icon(
                        isCompleted ? Icons.check_circle : Icons.radio_button_unchecked,
                        color: isCompleted ? AppColors.primaryGreen : Colors.grey,
                        size: 28,
                      ),
                      onPressed: isCompleted ? null : () => _completeTask(taskId),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  t['title'] ?? 'Task',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    decoration: isCompleted ? TextDecoration.lineThrough : null,
                                    color: isCompleted ? Colors.grey : Colors.black87,
                                  ),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: priorityColor.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  priority.toUpperCase(),
                                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: priorityColor),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            t['reason'] ?? t['description'] ?? '',
                            style: TextStyle(fontSize: 13, color: Colors.grey[700]),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const Divider(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.calendar_today_rounded, size: 14, color: Colors.grey[600]),
                        const SizedBox(width: 6),
                        Text(
                          "Due: ${t['due_at'] != null ? t['due_at'].toString().substring(0, 10) : 'Today'}",
                          style: TextStyle(fontSize: 12, color: Colors.grey[700], fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                    if (isCompleted)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.primaryGreen.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text("COMPLETED", style: TextStyle(color: AppColors.primaryGreen, fontWeight: FontWeight.bold, fontSize: 11)),
                      )
                    else
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          OutlinedButton.icon(
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              side: const BorderSide(color: Colors.blue),
                            ),
                            onPressed: () => _postponeTask(taskId),
                            icon: const Icon(Icons.schedule_rounded, size: 14, color: Colors.blue),
                            label: const Text("Postpone (+2d)", style: TextStyle(fontSize: 11, color: Colors.blue)),
                          ),
                          const SizedBox(width: 8),
                          OutlinedButton.icon(
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              side: const BorderSide(color: Colors.orange),
                            ),
                            onPressed: () => _skipTaskWithConfirmation(t),
                            icon: const Icon(Icons.skip_next_rounded, size: 14, color: Colors.orange),
                            label: const Text("Skip", style: TextStyle(fontSize: 11, color: Colors.orange)),
                          ),
                        ],
                      ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      appBar: AppBar(
        title: const Text("Farm Tasks & Smart Reminders"),
        backgroundColor: AppColors.primaryGreen,
        foregroundColor: Colors.white,
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          tabs: const [
            Tab(icon: Icon(Icons.today_rounded), text: "Today's Priorities"),
            Tab(icon: Icon(Icons.calendar_view_week_rounded), text: "7-Day Week Plan"),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: "Refresh Tasks",
            onPressed: _loadTasks,
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: _isLoading
              ? const Center(child: CircularProgressIndicator(color: AppColors.primaryGreen))
              : (_errorMessage != null
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
                      ),
                    )
                  : TabBarView(
                      controller: _tabController,
                      children: [
                        _buildTaskList(_todayTasks),
                        _buildTaskList(_weekTasks),
                      ],
                    )),
        ),
      ),
    );
  }
}
