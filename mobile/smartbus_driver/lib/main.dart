import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;

const _apiBaseUrl = String.fromEnvironment(
  'SMARTBUS_API_BASE_URL',
  defaultValue: 'https://replace-with-your-smartbus-domain.example/api/',
);
const _brand = Color(0xFF59D7D0);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SmartBusDriverApp());
}

class SmartBusDriverApp extends StatelessWidget {
  const SmartBusDriverApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'SmartBus Conducteur',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          brightness: Brightness.dark,
          colorScheme: ColorScheme.fromSeed(
            seedColor: _brand,
            brightness: Brightness.dark,
            surface: const Color(0xFF131F30),
          ),
          scaffoldBackgroundColor: const Color(0xFF0D1624),
          useMaterial3: true,
          inputDecorationTheme: const InputDecorationTheme(
            border: OutlineInputBorder(),
          ),
        ),
        home: const DriverHomePage(),
      );
}

class AssignedBus {
  const AssignedBus({
    required this.id,
    required this.registration,
    required this.status,
  });

  final int id;
  final String registration;
  final String status;

  factory AssignedBus.fromJson(Map<String, dynamic> json) => AssignedBus(
        id: json['id'] as int,
        registration: json['registration'] as String,
        status: json['status'] as String,
      );
}

class SmartBusApi {
  SmartBusApi({http.Client? client}) : _client = client ?? http.Client() {
    final uri = Uri.parse(_apiBaseUrl);
    final isAndroidEmulator = Platform.isAndroid &&
        (uri.host == '10.0.2.2' || uri.host == '10.0.3.2');
    if (uri.scheme != 'https' &&
        !(kDebugMode && isAndroidEmulator && uri.scheme == 'http')) {
      throw const SmartBusApiException(
        'Configure une URL HTTPS accessible pour l’API SmartBus.',
      );
    }
    if (uri.host.contains('replace-with-your-smartbus-domain')) {
      throw const SmartBusApiException(
        'L’adresse de l’API n’est pas encore configurée.',
      );
    }
    _baseUri = uri;
  }

  final http.Client _client;
  late final Uri _baseUri;

  Future<Map<String, dynamic>> login(
    String username,
    String password,
  ) async {
    final data = await _request(
      'POST',
      'auth/login/',
      body: {'username': username, 'password': password},
    );
    final user = data['user'] as Map<String, dynamic>;
    if (user['role'] != 'DRIVER') {
      throw const SmartBusApiException(
        'Ce compte n’a pas le rôle Conducteur.',
      );
    }
    return data;
  }

  Future<List<AssignedBus>> getAssignedBuses(String token) async {
    final data = await _request(
      'GET',
      'tracking/positions/my-buses/',
      token: token,
    );
    return (data as List<dynamic>)
        .map((item) => AssignedBus.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<void> reportPosition(String token, int busId, Position position) async {
    await _request(
      'POST',
      'tracking/positions/report/',
      token: token,
      body: {
        'bus': busId,
        'latitude': position.latitude,
        'longitude': position.longitude,
        'speed_kph':
            position.speed.isFinite ? (position.speed * 3.6).clamp(0, 400) : 0,
        'heading': position.heading.isFinite
            ? position.heading.round().clamp(0, 359)
            : 0,
      },
    );
  }

  Future<void> logout(String token) async {
    await _request('POST', 'auth/logout/', token: token);
  }

  Future<dynamic> _request(
    String method,
    String path, {
    String? token,
    Map<String, dynamic>? body,
  }) async {
    final uri = _baseUri.resolve(path);
    final headers = <String, String>{'Accept': 'application/json'};
    if (token != null) headers['Authorization'] = 'Token $token';
    if (body != null) headers['Content-Type'] = 'application/json';
    late final http.Response response;
    try {
      final request = http.Request(method, uri)..headers.addAll(headers);
      if (body != null) {
        request.body = _encodeJson(body);
      }
      final streamed = await _client.send(request).timeout(
            const Duration(seconds: 15),
          );
      response = await http.Response.fromStream(streamed).timeout(
        const Duration(seconds: 15),
      );
    } on TimeoutException {
      throw const SmartBusApiException(
        'Le serveur met trop de temps à répondre. Vérifie la connexion.',
      );
    } on SocketException {
      throw const SmartBusApiException(
        'Serveur inaccessible. Vérifie Internet et l’adresse API.',
      );
    } on http.ClientException {
      throw const SmartBusApiException(
        'Connexion au serveur impossible. Réessaie.',
      );
    }

    if (response.statusCode == 204) return null;
    late final dynamic decoded;
    try {
      decoded = _decodeJson(response.body);
    } on FormatException {
      throw SmartBusApiException(
        'Le serveur a renvoyé une réponse invalide (${response.statusCode}).',
        statusCode: response.statusCode,
      );
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = decoded is Map<String, dynamic>
          ? (decoded['detail']?.toString() ??
              decoded.values.map((value) => value.toString()).join(' '))
          : 'Erreur du serveur (${response.statusCode}).';
      throw SmartBusApiException(message, statusCode: response.statusCode);
    }
    return decoded;
  }

  void close() => _client.close();
}

String _encodeJson(Map<String, dynamic> value) {
  return jsonEncode(value);
}

dynamic _decodeJson(String value) => jsonDecode(value);

class SmartBusApiException implements Exception {
  const SmartBusApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class DriverHomePage extends StatefulWidget {
  const DriverHomePage({super.key});

  @override
  State<DriverHomePage> createState() => _DriverHomePageState();
}

class _DriverHomePageState extends State<DriverHomePage>
    with WidgetsBindingObserver {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.unlocked_this_device,
    ),
  );

  SmartBusApi? _api;
  SmartBusApi get _client => _api!;
  final _username = TextEditingController();
  final _password = TextEditingController();
  StreamSubscription<Position>? _positionSubscription;
  List<AssignedBus> _buses = const [];
  String? _token;
  int? _selectedBusId;
  String _status = 'Partage GPS arrêté.';
  bool _isLoading = false;
  bool _isSharing = false;
  bool _hasConfigurationError = false;
  bool _sendingPosition = false;
  DateTime? _lastSentAt;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    try {
      _api = SmartBusApi();
      unawaited(_restoreSession());
    } on SmartBusApiException catch (error) {
      _hasConfigurationError = true;
      _status = error.message;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    unawaited(_stopSharing());
    _username.dispose();
    _password.dispose();
    _api?.close();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.detached && _isSharing) {
      unawaited(_stopSharing());
    }
  }

  Future<void> _restoreSession() async {
    try {
      final savedToken = await _storage.read(key: 'driver_api_token');
      if (savedToken == null || !mounted) return;
      setState(() => _isLoading = true);
      final buses = await _client.getAssignedBuses(savedToken);
      if (!mounted) return;
      setState(() {
        _token = savedToken;
        _buses = buses;
        _selectedBusId = buses.isEmpty ? null : buses.first.id;
        _status = buses.isEmpty
            ? 'Aucun bus affecté. Contacte le gestionnaire.'
            : 'Session restaurée. Le partage est arrêté.';
      });
    } on SmartBusApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _status = error.statusCode == 401 || error.statusCode == 403
            ? 'Session expirée. Reconnecte-toi.'
            : 'Serveur inaccessible. Vérifie Internet puis reconnecte-toi.';
      });
    } on Object catch (error) {
      if (mounted) {
        setState(() => _status = 'Impossible de restaurer la session : $error');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _login() async {
    FocusScope.of(context).unfocus();
    setState(() {
      _isLoading = true;
      _status = 'Connexion…';
    });
    try {
      final result = await _client.login(_username.text.trim(), _password.text);
      final token = result['token'] as String;
      final buses = await _client.getAssignedBuses(token);
      await _storage.write(key: 'driver_api_token', value: token);
      if (!mounted) return;
      setState(() {
        _token = token;
        _buses = buses;
        _selectedBusId = buses.isEmpty ? null : buses.first.id;
        _password.clear();
        _status = buses.isEmpty
            ? 'Aucun bus affecté à ton compte.'
            : 'Connecté. Le partage GPS est arrêté.';
      });
    } on SmartBusApiException catch (error) {
      if (mounted) setState(() => _status = error.message);
    } on Object catch (error) {
      if (mounted) setState(() => _status = 'Connexion impossible : $error');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _startSharing() async {
    if (_token == null || _selectedBusId == null) {
      setState(() => _status = 'Connecte-toi et sélectionne un bus affecté.');
      return;
    }
    setState(() => _isLoading = true);
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        throw const SmartBusApiException(
          'Active la localisation du téléphone puis réessaie.',
        );
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        throw const SmartBusApiException(
          'La permission de localisation est nécessaire pour partager le trajet.',
        );
      }

      if (!mounted) return;
      final settings = _locationSettings();
      final stream = Geolocator.getPositionStream(locationSettings: settings);
      _positionSubscription = stream.listen(
        _onPosition,
        onError: (Object error) {
          if (mounted) setState(() => _status = 'Erreur GPS : $error');
        },
      );
      setState(() {
        _isSharing = true;
        _status =
            'Partage actif pour ${_selectedBus!.registration}. Arrête-le à la fin du service.';
      });
    } on SmartBusApiException catch (error) {
      setState(() => _status = error.message);
    } on Object catch (error) {
      if (mounted) {
        setState(() => _status = 'Impossible de démarrer le GPS : $error');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  LocationSettings _locationSettings() {
    if (Platform.isAndroid) {
      return AndroidSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 0,
        intervalDuration: const Duration(seconds: 10),
        foregroundNotificationConfig: const ForegroundNotificationConfig(
          notificationTitle: 'SmartBus · partage GPS actif',
          notificationText:
              'Ta position est partagée avec ton agence. Appuie sur Arrêter dans l’application pour terminer.',
          enableWakeLock: true,
          setOngoing: true,
        ),
      );
    }
    if (Platform.isIOS || Platform.isMacOS) {
      return AppleSettings(
        accuracy: LocationAccuracy.best,
        activityType: ActivityType.automotiveNavigation,
        distanceFilter: 0,
        pauseLocationUpdatesAutomatically: false,
        showBackgroundLocationIndicator: true,
        allowBackgroundLocationUpdates: true,
      );
    }
    return const LocationSettings(
      accuracy: LocationAccuracy.high,
      distanceFilter: 0,
    );
  }

  AssignedBus? get _selectedBus {
    for (final bus in _buses) {
      if (bus.id == _selectedBusId) return bus;
    }
    return null;
  }

  Future<void> _onPosition(Position position) async {
    final now = DateTime.now();
    if (_lastSentAt != null &&
        now.difference(_lastSentAt!) < const Duration(seconds: 10)) {
      return;
    }
    if (_sendingPosition) return;
    final token = _token;
    final busId = _selectedBusId;
    if (token == null || busId == null) return;
    _sendingPosition = true;
    _lastSentAt = now;
    try {
      await _client.reportPosition(token, busId, position);
      if (mounted) {
        setState(() {
          _status =
              'Position envoyée à ${now.toLocal().toString().substring(11, 19)}'
              ' · précision ±${position.accuracy.round()} m';
        });
      }
    } on SmartBusApiException catch (error) {
      if (!mounted) return;
      setState(() => _status = 'Envoi impossible : ${error.message}');
      if (error.statusCode == 401 ||
          error.statusCode == 403 ||
          error.message.contains('expirée') ||
          error.message.contains('Permission refusée')) {
        await _stopSharing();
      }
    } finally {
      _sendingPosition = false;
    }
  }

  Future<void> _stopSharing() async {
    await _positionSubscription?.cancel();
    _positionSubscription = null;
    if (mounted && _isSharing) {
      setState(() {
        _isSharing = false;
        _lastSentAt = null;
        _status = 'Partage GPS arrêté.';
      });
    } else {
      _isSharing = false;
      _lastSentAt = null;
    }
  }

  Future<void> _logout() async {
    await _stopSharing();
    final token = _token;
    if (token != null) {
      try {
        await _client.logout(token);
      } on SmartBusApiException {
        // Local credentials are still erased if the server cannot be reached.
      }
    }
    await _storage.delete(key: 'driver_api_token');
    if (!mounted) return;
    setState(() {
      _token = null;
      _buses = const [];
      _selectedBusId = null;
      _status = 'Déconnecté.';
    });
  }

  Widget _buildLogin() => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _username,
            textInputAction: TextInputAction.next,
            autofillHints: const [AutofillHints.username],
            decoration: const InputDecoration(labelText: 'Nom d’utilisateur'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _password,
            obscureText: true,
            onSubmitted: (_) => _login(),
            autofillHints: const [AutofillHints.password],
            decoration: const InputDecoration(labelText: 'Mot de passe'),
          ),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: _isLoading ? null : _login,
            child: const Text('Se connecter comme conducteur'),
          ),
        ],
      );

  Widget _buildControls() => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DropdownButtonFormField<int>(
            value: _selectedBusId,
            decoration: const InputDecoration(labelText: 'Bus affecté'),
            items: _buses
                .map(
                  (bus) => DropdownMenuItem<int>(
                    value: bus.id,
                    child: Text('${bus.registration} · ${bus.status}'),
                  ),
                )
                .toList(growable: false),
            onChanged: _isSharing
                ? null
                : (value) => setState(() => _selectedBusId = value),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: _isLoading || _isSharing || _buses.isEmpty
                ? null
                : _startSharing,
            icon: const Icon(Icons.my_location),
            label: const Text('Démarrer le partage GPS'),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: _isSharing ? _stopSharing : null,
            icon: const Icon(Icons.stop_circle_outlined),
            label: const Text('Arrêter le partage'),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: _isLoading ? null : _logout,
            child: const Text('Se déconnecter'),
          ),
        ],
      );

  @override
  Widget build(BuildContext context) {
    final connected = _token != null;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                const SizedBox(height: 18),
                Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: _brand,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Text(
                        'SB',
                        style: TextStyle(
                          color: Color(0xFF0D2026),
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Text(
                      'SMARTBUS',
                      style: TextStyle(
                        color: _brand,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 34),
                Text(
                  connected ? 'Bonjour conducteur' : 'Partager ma position',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Le partage démarre uniquement après ton action. Arrête-le à la fin du service.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFF9AAABD),
                        height: 1.5,
                      ),
                ),
                const SizedBox(height: 24),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          _isSharing ? Icons.gps_fixed : Icons.gps_not_fixed,
                          color: _isSharing ? _brand : Colors.blueGrey,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            _status,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                if (_isLoading) ...[
                  const SizedBox(height: 12),
                  const LinearProgressIndicator(),
                ],
                const SizedBox(height: 18),
                if (_hasConfigurationError)
                  const Text(
                    'Configure SMARTBUS_API_BASE_URL avant de compiler.',
                    style: TextStyle(color: Colors.orangeAccent),
                  )
                else if (connected)
                  _buses.isEmpty
                      ? const Text(
                          'Aucun bus n’est affecté à ce compte. Contacte le gestionnaire de flotte.',
                        )
                      : _buildControls()
                else
                  _buildLogin(),
                const SizedBox(height: 26),
                const Divider(color: Color(0xFF29394E)),
                const SizedBox(height: 12),
                const Text(
                  'Suivi visible, activé volontairement par le chauffeur et limité à son bus affecté.',
                  style: TextStyle(
                    color: Color(0xFF8395AA),
                    fontSize: 12,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 18),
                const Center(
                  child: Text(
                    'Créé par Nathan Zoua · NZ',
                    style: TextStyle(color: Color(0xFF6F8198), fontSize: 11),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
