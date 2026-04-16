import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

/// FCM Service for handling Firebase Cloud Messaging in Flutter mobile app
class FCMService {
  static final FCMService _instance = FCMService._internal();
  factory FCMService() => _instance;
  FCMService._internal();

  final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  
  // API endpoint for device registration
  static const String _baseUrl = 'http://127.0.0.1:8000';
  static const String _deviceEndpoint = '/api/v1/devices/';
  
  // Store the current FCM token
  String? _fcmToken;
  
  // Callback for token refresh
  Function(String)? onTokenRefreshed;
  
  // Getters
  String? get fcmToken => _fcmToken;
  bool get isInitialized => _fcmToken != null;

  /// Initialize FCM service
  Future<void> initialize() async {
    try {
      // Request notification permissions
      await requestPermission();
      
      // Get FCM token
      _fcmToken = await getToken();
      
      // Listen for token refresh
      _setupTokenRefreshListener();
      
      if (kDebugMode) {
        print('[FCM] Initialized with token: ${_fcmToken?.substring(0, 20)}...');
      }
    } catch (e) {
      if (kDebugMode) {
        print('[FCM] Initialization error: $e');
      }
      rethrow;
    }
  }

  /// Request notification permissions from the user
  Future<bool> requestPermission() async {
    try {
      // For iOS/macOS
      final settings = await _firebaseMessaging.requestPermission(
        alert: true,
        announcement: false,
        badge: true,
        carPlay: false,
        criticalAlert: false,
        provisional: false,
        sound: true,
      );
      
      if (kDebugMode) {
        print('[FCM] Permission status: ${settings.authorizationStatus}');
      }
      
      return settings.authorizationStatus == AuthorizationStatus.authorized ||
             settings.authorizationStatus == AuthorizationStatus.provisional;
    } catch (e) {
      if (kDebugMode) {
        print('[FCM] Permission request error: $e');
      }
      return false;
    }
  }

  /// Get the current FCM token
  Future<String> getToken() async {
    try {
      // Get token with vapid key (optional but recommended)
      final token = await _firebaseMessaging.getToken(
        vapidKey: 'YOUR_VAPID_KEY_HERE', // Replace with your VAPID key
      );
      
      if (token == null) {
        throw Exception('Failed to get FCM token');
      }
      
      _fcmToken = token;
      return token;
    } catch (e) {
      if (kDebugMode) {
        print('[FCM] Error getting token: $e');
      }
      rethrow;
    }
  }

  /// Setup listener for token refresh
  void _setupTokenRefreshListener() {
    _firebaseMessaging.onTokenRefresh.listen((newToken) {
      if (kDebugMode) {
        print('[FCM] Token refreshed: ${newToken.substring(0, 20)}...');
      }
      
      _fcmToken = newToken;
      
      // Notify callback if registered
      onTokenRefreshed?.call(newToken);
    });
  }

  /// Register device with backend
  /// 
  /// [token] - FCM token from getToken()
  /// [jwtToken] - JWT authentication token
  /// [deviceType] - Device type: 'android', 'ios', or 'web'
  Future<DeviceRegistrationResult> registerDevice({
    required String token,
    required String jwtToken,
    required String deviceType,
  }) async {
    try {
      final url = Uri.parse('$_baseUrl$_deviceEndpoint');
      
      final payload = {
        'registration_id': token,
        'device_type': deviceType,
        'active': true,
      };
      
      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $jwtToken',
        },
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 30));
      
      if (response.statusCode == 201 || response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        if (kDebugMode) {
          print('[FCM] Device registered successfully: ${data['id']}');
        }
        
        return DeviceRegistrationResult(
          success: true,
          deviceId: data['id']?.toString(),
          message: 'Device registered successfully',
        );
      } else if (response.statusCode == 401) {
        return DeviceRegistrationResult(
          success: false,
          error: DeviceRegistrationError.unauthorized,
          message: 'Authentication failed. Please login again.',
        );
      } else {
        final errorBody = response.body.isNotEmpty 
            ? jsonDecode(response.body) 
            : {};
        
        return DeviceRegistrationResult(
          success: false,
          error: DeviceRegistrationError.serverError,
          message: errorBody['detail'] ?? 'Failed to register device',
          statusCode: response.statusCode,
        );
      }
    } on http.ClientException catch (e) {
      if (kDebugMode) {
        print('[FCM] Network error: ${e.message}');
      }
      
      return DeviceRegistrationResult(
        success: false,
        error: DeviceRegistrationError.networkError,
        message: 'Network error: ${e.message}',
      );
    } catch (e) {
      if (kDebugMode) {
        print('[FCM] Registration error: $e');
      }
      
      return DeviceRegistrationResult(
        success: false,
        error: DeviceRegistrationError.unknown,
        message: 'Unexpected error: $e',
      );
    }
  }

  /// Update device registration (e.g., on token refresh)
  Future<DeviceRegistrationResult> updateDevice({
    required String deviceId,
    required String jwtToken,
    String? registrationId,
    bool? active,
  }) async {
    try {
      final url = Uri.parse('$_baseUrl$_deviceEndpoint$deviceId/');
      
      final payload = <String, dynamic>{};
      if (registrationId != null) {
        payload['registration_id'] = registrationId;
      }
      if (active != null) {
        payload['active'] = active;
      }
      
      final response = await http.put(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $jwtToken',
        },
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 30));
      
      if (response.statusCode == 200) {
        return DeviceRegistrationResult(
          success: true,
          deviceId: deviceId,
          message: 'Device updated successfully',
        );
      }
      
      return DeviceRegistrationResult(
        success: false,
        error: DeviceRegistrationError.serverError,
        message: 'Failed to update device',
        statusCode: response.statusCode,
      );
    } catch (e) {
      if (kDebugMode) {
        print('[FCM] Update error: $e');
      }
      
      return DeviceRegistrationResult(
        success: false,
        error: DeviceRegistrationError.unknown,
        message: 'Unexpected error: $e',
      );
    }
  }

  /// Delete device registration
  Future<bool> unregisterDevice({
    required String deviceId,
    required String jwtToken,
  }) async {
    try {
      final url = Uri.parse('$_baseUrl$_deviceEndpoint$deviceId/');
      
      final response = await http.delete(
        url,
        headers: {
          'Authorization': 'Bearer $jwtToken',
        },
      ).timeout(const Duration(seconds: 30));
      
      return response.statusCode == 204;
    } catch (e) {
      if (kDebugMode) {
        print('[FCM] Unregister error: $e');
      }
      return false;
    }
  }

  /// Get device type string based on platform
  static String getDeviceType() {
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      return 'ios';
    } else if (defaultTargetPlatform == TargetPlatform.android) {
      return 'android';
    }
    return 'web';
  }

  /// Setup foreground message handler
  void onForegroundMessage(Function(Message) handler) {
    FirebaseMessaging.onMessage.listen((message) {
      handler(message);
    });
  }

  /// Setup background message handler
  void onBackgroundMessage(Function(Message) handler) {
    FirebaseMessaging.onBackgroundMessage((message) async {
      handler(message);
    });
  }

  /// Subscribe to a topic
  Future<bool> subscribeToTopic(String topic) async {
    try {
      await _firebaseMessaging.subscribeToTopic(topic);
      return true;
    } catch (e) {
      if (kDebugMode) {
        print('[FCM] Subscribe error: $e');
      }
      return false;
    }
  }

  /// Unsubscribe from a topic
  Future<bool> unsubscribeFromTopic(String topic) async {
    try {
      await _firebaseMessaging.unsubscribeFromTopic(topic);
      return true;
    } catch (e) {
      if (kDebugMode) {
        print('[FCM] Unsubscribe error: $e');
      }
      return false;
    }
  }
}

/// Device registration result
class DeviceRegistrationResult {
  final bool success;
  final String? deviceId;
  final String message;
  final DeviceRegistrationError? error;
  final int? statusCode;

  DeviceRegistrationResult({
    required this.success,
    this.deviceId,
    required this.message,
    this.error,
    this.statusCode,
  });
}

/// Device registration errors
enum DeviceRegistrationError {
  unauthorized,
  networkError,
  serverError,
  unknown,
}