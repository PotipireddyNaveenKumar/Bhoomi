import 'package:flutter_test/flutter_test.dart';
import 'package:bhoomi_mobile/core/constants/api_endpoints.dart';

void main() {
  group('ApiEndpoints Canonical Consolidation Tests', () {
    test('chat constant points to canonical assistant/chat', () {
      expect(ApiEndpoints.chat, contains('/assistant/chat'));
      expect(ApiEndpoints.chat.endsWith('/api/v1/assistant/chat'), isTrue);
    });

    test('simulationWhatIf constant points to canonical simulation/what-if', () {
      expect(ApiEndpoints.simulationWhatIf, contains('/simulation/what-if'));
      expect(ApiEndpoints.simulationWhatIf.endsWith('/api/v1/simulation/what-if'), isTrue);
    });

    test('simulationRun alias points to canonical simulation/what-if for backwards compatibility', () {
      expect(ApiEndpoints.simulationRun, equals(ApiEndpoints.simulationWhatIf));
    });
  });
}
