import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bhoomi_mobile/main.dart';
import 'package:bhoomi_mobile/features/command_center/farm_command_center_screen.dart';
import 'package:bhoomi_mobile/features/voice/voice_assistant_screen.dart';
import 'package:bhoomi_mobile/features/vision/leaf_scanner_screen.dart';
import 'package:bhoomi_mobile/features/profit/profit_simulator_screen.dart';
import 'package:bhoomi_mobile/features/tasks/tasks_screen.dart';
import 'package:bhoomi_mobile/features/market/market_intelligence_screen.dart';

Widget makeTestable(Widget child) {
  return MaterialApp(
    home: child,
  );
}

void main() {
  testWidgets('BhoomiApp smoke and initialization test', (WidgetTester tester) async {
    await tester.pumpWidget(const BhoomiApp(initialLocale: Locale('en')));
    await tester.pump();

    expect(find.byType(MaterialApp), findsOneWidget);
    expect(find.text('BHOOMI'), findsOneWidget);
    
    // Advance timer past splash delay
    await tester.pump(const Duration(milliseconds: 1800));
    await tester.pump(const Duration(milliseconds: 300));
  });

  testWidgets('FarmCommandCenterScreen renders correctly', (WidgetTester tester) async {
    await tester.pumpWidget(makeTestable(const FarmCommandCenterScreen()));
    await tester.pump();

    expect(find.text('BHOOMI Command Center'), findsOneWidget);
    expect(find.text('Today'), findsOneWidget);
    expect(find.text('My Crop'), findsOneWidget);
  });

  testWidgets('VoiceAssistantScreen renders voice orb and controls', (WidgetTester tester) async {
    await tester.pumpWidget(makeTestable(const VoiceAssistantScreen()));
    await tester.pump();

    expect(find.text('BHOOMI Voice Assistant'), findsOneWidget);
    expect(find.text('Tap microphone to speak with BHOOMI'), findsOneWidget);
  });

  testWidgets('LeafScannerScreen renders camera controls and options', (WidgetTester tester) async {
    await tester.pumpWidget(makeTestable(const LeafScannerScreen()));
    await tester.pump();

    expect(find.text('Plant Pathology Scanner'), findsOneWidget);
    expect(find.text('Capture Photo'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
  });

  testWidgets('ProfitSimulatorScreen renders what-if sliders', (WidgetTester tester) async {
    await tester.pumpWidget(makeTestable(const ProfitSimulatorScreen()));
    await tester.pump();

    expect(find.text('What-If Farm Simulator'), findsOneWidget);
    expect(find.text('Market Price Shift'), findsOneWidget);
  });

  testWidgets('TasksScreen renders task manager UI', (WidgetTester tester) async {
    await tester.pumpWidget(makeTestable(const TasksScreen()));
    await tester.pump();

    expect(find.text('Farm Tasks & Smart Reminders'), findsOneWidget);
  });

  testWidgets('MarketIntelligenceScreen renders commodity prices', (WidgetTester tester) async {
    await tester.pumpWidget(makeTestable(const MarketIntelligenceScreen()));
    await tester.pump();

    expect(find.text('Market & Mandi Intelligence'), findsOneWidget);
    expect(find.text('Guntur Mandi (Benchmark)'), findsOneWidget);
  });
}
