// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'file_picker_stub.dart';

void pickImageFile(FilePickedCallback onPicked) {
  final uploadInput = html.FileUploadInputElement()..accept = 'image/*';
  uploadInput.click();

  uploadInput.onChange.listen((e) {
    final files = uploadInput.files;
    if (files != null && files.isNotEmpty) {
      final file = files[0];
      final reader = html.FileReader();
      reader.onLoadEnd.listen((e) {
        if (reader.result != null) {
          final bytes = (reader.result as dynamic) as List<int>;
          onPicked(bytes, file.name);
        }
      });
      reader.readAsArrayBuffer(file);
    }
  });
}
