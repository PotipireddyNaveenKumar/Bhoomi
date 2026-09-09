import 'package:shared_preferences/shared_preferences.dart';

class LocalStorageService {
  static const String _tokenKey = "auth_token";
  static const String _langKey = "user_language";
  static const String _userNameKey = "user_name";
  static const String _farmerIdKey = "farmer_id";

  static Future<void> saveAuthData({
    required String token,
    required String farmerId,
    required String name,
    required String language,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    await prefs.setString(_farmerIdKey, farmerId);
    await prefs.setString(_userNameKey, name);
    await prefs.setString(_langKey, language);
  }

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  static Future<String> getLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_langKey) ?? "en";
  }

  static Future<void> setLanguage(String lang) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_langKey, lang);
  }

  static Future<String?> getUserName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userNameKey);
  }

  static const String _locationKey = "farm_location";
  static const String _areaKey = "farm_area";
  static const String _cropKey = "farm_crop";
  static const String _varietyKey = "farm_variety";
  static const String _soilKey = "farm_soil";
  static const String _irrigationKey = "farm_irrigation";
  static const String _sowingDateKey = "farm_sowing_date";
  static const String _contactPrefKey = "farm_contact_pref";

  static Future<void> saveFarmProfile({
    required String name,
    required String location,
    required String area,
    required String crop,
    required String variety,
    required String soil,
    required String irrigation,
    String? sowingDate,
    String? contactPref,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userNameKey, name);
    await prefs.setString(_locationKey, location);
    await prefs.setString(_areaKey, area);
    await prefs.setString(_cropKey, crop);
    await prefs.setString(_varietyKey, variety);
    await prefs.setString(_soilKey, soil);
    await prefs.setString(_irrigationKey, irrigation);
    if (sowingDate != null) await prefs.setString(_sowingDateKey, sowingDate);
    if (contactPref != null) await prefs.setString(_contactPrefKey, contactPref);
  }

  static Future<String?> getFarmerId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_farmerIdKey);
  }

  static Future<Map<String, String>> getFarmProfile() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      "name": prefs.getString(_userNameKey) ?? "",
      "location": prefs.getString(_locationKey) ?? "",
      "area": prefs.getString(_areaKey) ?? "",
      "crop": prefs.getString(_cropKey) ?? "",
      "variety": prefs.getString(_varietyKey) ?? "",
      "soil": prefs.getString(_soilKey) ?? "",
      "irrigation": prefs.getString(_irrigationKey) ?? "",
      "sowing_date": prefs.getString(_sowingDateKey) ?? "",
      "stage": prefs.getString(_cropKey) != null ? "Active" : "",
      "contact_pref": prefs.getString(_contactPrefKey) ?? "Voice & SMS",
    };
  }

  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }
}
