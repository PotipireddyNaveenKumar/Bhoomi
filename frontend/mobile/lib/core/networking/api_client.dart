import 'dart:convert';
import 'package:http/http.dart' as http;
import '../storage/secure_storage.dart';

class ApiClient {
  static Future<Map<String, String>> _getHeaders() async {
    final token = await LocalStorageService.getToken();
    final lang = await LocalStorageService.getLanguage();
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Accept-Language': lang,
    };
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  static Future<http.Response> get(String url) async {
    final headers = await _getHeaders();
    return await http.get(Uri.parse(url), headers: headers);
  }

  static Future<http.Response> post(String url, Map<String, dynamic> body) async {
    final headers = await _getHeaders();
    final lang = await LocalStorageService.getLanguage();
    final mutableBody = Map<String, dynamic>.from(body);
    if (!mutableBody.containsKey('language')) {
      mutableBody['language'] = lang;
    }
    return await http.post(
      Uri.parse(url),
      headers: headers,
      body: jsonEncode(mutableBody),
    );
  }

  static Future<http.Response> postMultipart(
    String url, {
    required List<int> fileBytes,
    required String filename,
    String fieldName = "file",
    Map<String, String>? fields,
  }) async {
    final token = await LocalStorageService.getToken();
    final lang = await LocalStorageService.getLanguage();
    final request = http.MultipartRequest('POST', Uri.parse(url));
    request.headers['Accept-Language'] = lang;
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }
    if (fields != null) {
      request.fields.addAll(fields);
    }
    if (!request.fields.containsKey('language')) {
      request.fields['language'] = lang;
    }
    request.files.add(http.MultipartFile.fromBytes(
      fieldName,
      fileBytes,
      filename: filename,
    ));
    final streamedResponse = await request.send();
    return await http.Response.fromStream(streamedResponse);
  }
}
