import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8001/api/v1',
);
const defaultOrganizationId = String.fromEnvironment(
  'DEFAULT_ORGANIZATION_ID',
  defaultValue: '',
);
const _tokenKey = 'fixflow_access_token';
const _storage = FlutterSecureStorage();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const FixFlowApp());
}

class FixFlowApp extends StatefulWidget {
  const FixFlowApp({super.key});

  @override
  State<FixFlowApp> createState() => _FixFlowAppState();
}

class _FixFlowAppState extends State<FixFlowApp> {
  final _api = FixFlowApi(apiBaseUrl);
  String? _token;
  Map<String, dynamic>? _profile;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    try {
      final saved = await _storage.read(key: _tokenKey);
      if (saved != null) {
        final profile = await _api.me(saved);
        if (profile['role'] == 'TECHNICIAN') {
          _token = saved;
          _profile = profile;
        } else {
          await _storage.delete(key: _tokenKey);
        }
      }
    } catch (_) {
      await _storage.delete(key: _tokenKey);
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _signIn(String email, String password, String organizationId) async {
    final token = await _api.login(email, password, organizationId);
    final profile = await _api.me(token);
    if (profile['role'] != 'TECHNICIAN') {
      throw const ApiException('В мобильном приложении доступен вход для специалиста.');
    }
    await _storage.write(key: _tokenKey, value: token);
    if (mounted) setState(() { _token = token; _profile = profile; });
  }

  Future<void> _signOut() async {
    await _storage.delete(key: _tokenKey);
    if (mounted) setState(() { _token = null; _profile = null; });
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'FixFlow',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff168c78)),
          useMaterial3: true,
          scaffoldBackgroundColor: const Color(0xfff5f8f7),
          inputDecorationTheme: const InputDecorationTheme(
            border: OutlineInputBorder(),
            filled: true,
            fillColor: Colors.white,
          ),
        ),
        home: _loading
            ? const Scaffold(body: Center(child: CircularProgressIndicator()))
            : _token == null
                ? LoginScreen(onSignIn: _signIn)
                : TechnicianHome(
                    api: _api,
                    token: _token!,
                    profile: _profile ?? const {},
                    onSignOut: _signOut,
                  ),
      );
}

class FixFlowApi {
  FixFlowApi(this.baseUrl);
  final String baseUrl;
  final http.Client _client = http.Client();

  Future<dynamic> _call(String path, {String? token, String method = 'GET', Object? body, Map<String, String> extraHeaders = const {}}) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = <String, String>{'Accept': 'application/json'};
    if (token != null) headers['Authorization'] = 'Bearer $token';
    if (body != null) headers['Content-Type'] = 'application/json';
    headers.addAll(extraHeaders);
    late http.Response response;
    try {
      final request = http.Request(method, uri)..headers.addAll(headers);
      if (body != null) request.body = jsonEncode(body);
      response = await http.Response.fromStream(await _client.send(request).timeout(const Duration(seconds: 20)));
    } catch (_) {
      throw const ApiException('Нет связи с FixFlow. Проверьте интернет и адрес сервера.');
    }
    dynamic decoded;
    if (response.body.isNotEmpty) {
      try { decoded = jsonDecode(response.body); } catch (_) { decoded = null; }
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final detail = decoded is Map ? decoded['detail'] : null;
      throw ApiException(detail?.toString() ?? 'Ошибка сервера (${response.statusCode}).');
    }
    return decoded;
  }

  Future<String> login(String email, String password, String organizationId) async {
    final result = await _call('/auth/login', method: 'POST', body: {
      'email': email,
      'password': password,
      'organization_id': organizationId,
    });
    return (result as Map<String, dynamic>)['access_token'] as String;
  }

  Future<Map<String, dynamic>> me(String token) async =>
      Map<String, dynamic>.from(await _call('/auth/me', token: token) as Map);

  Future<List<TechnicianTask>> tasks(String token) async {
    final raw = await _call('/technician/assignments', token: token) as List<dynamic>;
    final results = await Future.wait(raw.map((entry) async {
      final assignment = Map<String, dynamic>.from(entry as Map);
      final request = Map<String, dynamic>.from(
        await _call('/requests/${assignment['request_id']}', token: token) as Map,
      );
      return TechnicianTask(assignment: assignment, request: request);
    }));
    return results;
  }

  Future<void> accept(String token, String assignmentId) async {
    await _call('/assignments/$assignmentId/accept', token: token, method: 'POST');
  }

  Future<void> setRequestStatus(String token, String requestId, String status) async {
    await _call('/requests/$requestId/status', token: token, method: 'PATCH', body: {'status': status});
  }

  Future<List<Map<String, dynamic>>> notes(String token, String requestId) async =>
      (await _call('/requests/$requestId/notes', token: token) as List<dynamic>)
          .map((item) => Map<String, dynamic>.from(item as Map)).toList();

  Future<void> addNote(String token, String requestId, String body) async {
    await _call('/requests/$requestId/notes', token: token, method: 'POST', body: {
        'body': body,
        'internal_only': false,
      }, extraHeaders: {'Idempotency-Key': 'mobile-${const Uuid().v4()}'});
  }
}

class ApiException implements Exception {
  const ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}

class TechnicianTask {
  const TechnicianTask({required this.assignment, required this.request});
  final Map<String, dynamic> assignment;
  final Map<String, dynamic> request;
  String get assignmentStatus => assignment['status'] as String? ?? '';
  String get requestStatus => request['status'] as String? ?? '';
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({required this.onSignIn, super.key});
  final Future<void> Function(String, String, String) onSignIn;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _organization = TextEditingController(text: defaultOrganizationId);
  bool _busy = false;
  bool _showPassword = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose(); _password.dispose(); _organization.dispose(); super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _busy = true; _error = null; });
    try {
      await widget.onSignIn(_email.text.trim(), _password.text, _organization.text.trim());
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 460),
                child: Form(
                  key: _formKey,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    const _Brand(),
                    const SizedBox(height: 28),
                    Text('Кабинет специалиста', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
                    const SizedBox(height: 8),
                    Text('Войдите, чтобы увидеть назначения и обновлять ход работ.', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.blueGrey)),
                    const SizedBox(height: 24),
                    TextFormField(controller: _email, keyboardType: TextInputType.emailAddress, autofillHints: const [AutofillHints.username], decoration: const InputDecoration(labelText: 'Электронная почта', prefixIcon: Icon(Icons.mail_outline)), validator: (v) => v == null || !v.contains('@') ? 'Введите рабочую почту' : null),
                    const SizedBox(height: 14),
                    TextFormField(controller: _password, obscureText: !_showPassword, autofillHints: const [AutofillHints.password], decoration: InputDecoration(labelText: 'Пароль', prefixIcon: const Icon(Icons.lock_outline), suffixIcon: IconButton(onPressed: () => setState(() => _showPassword = !_showPassword), icon: Icon(_showPassword ? Icons.visibility_off : Icons.visibility))), validator: (v) => v == null || v.isEmpty ? 'Введите пароль' : null),
                    const SizedBox(height: 14),
                    TextFormField(controller: _organization, decoration: const InputDecoration(labelText: 'ID организации', prefixIcon: Icon(Icons.business_outlined)), validator: (v) => v == null || v.trim().isEmpty ? 'Укажите ID организации' : null),
                    if (_error != null) ...[
                      const SizedBox(height: 14),
                      _ErrorBox(message: _error!),
                    ],
                    const SizedBox(height: 20),
                    FilledButton.icon(onPressed: _busy ? null : _submit, icon: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.login), label: Text(_busy ? 'Входим…' : 'Войти'), style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52))),
                    const SizedBox(height: 18),
                    Text('Сервер: $apiBaseUrl', textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.blueGrey)),
                  ]),
                ),
              ),
            ),
          ),
        ),
      );
}

class TechnicianHome extends StatefulWidget {
  const TechnicianHome({required this.api, required this.token, required this.profile, required this.onSignOut, super.key});
  final FixFlowApi api;
  final String token;
  final Map<String, dynamic> profile;
  final Future<void> Function() onSignOut;

  @override
  State<TechnicianHome> createState() => _TechnicianHomeState();
}

class _TechnicianHomeState extends State<TechnicianHome> {
  List<TechnicianTask> _tasks = const [];
  bool _loading = true;
  String? _error;
  String? _workingId;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final tasks = await widget.api.tasks(widget.token);
      if (mounted) setState(() => _tasks = tasks);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _perform(TechnicianTask task, String action) async {
    setState(() { _workingId = task.assignment['id'] as String?; _error = null; });
    try {
      final requestId = task.request['id'] as String;
      if (action == 'accept') {
        await widget.api.accept(widget.token, task.assignment['id'] as String);
      } else {
        await widget.api.setRequestStatus(widget.token, requestId, action);
      }
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _workingId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final name = widget.profile['name'] as String? ?? 'Специалист';
    return Scaffold(
      appBar: AppBar(
        title: const _Brand(compact: true),
        actions: [IconButton(tooltip: 'Выйти', onPressed: widget.onSignOut, icon: const Icon(Icons.logout))],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 28), children: [
          Text('Здравствуйте, $name', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text('Ваши назначения и текущие работы', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.blueGrey)),
          const SizedBox(height: 20),
          if (_error != null) ...[
            _ErrorBox(message: _error!),
            const SizedBox(height: 12),
          ],
          if (_loading && _tasks.isEmpty) const Padding(padding: EdgeInsets.all(36), child: Center(child: CircularProgressIndicator())),
          if (!_loading && _tasks.isEmpty && _error == null) const _EmptyTasks(),
          for (final task in _tasks) Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: _TaskCard(
              task: task,
              busy: _workingId == task.assignment['id'],
              onAction: (action) => _perform(task, action),
              onDetails: () => _openDetails(task),
            ),
          ),
        ]),
      ),
      floatingActionButton: FloatingActionButton.small(onPressed: _load, tooltip: 'Обновить', child: const Icon(Icons.refresh)),
    );
  }

  Future<void> _openDetails(TechnicianTask task) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => _TaskDetails(api: widget.api, token: widget.token, task: task),
    );
  }
}

class _TaskCard extends StatelessWidget {
  const _TaskCard({required this.task, required this.busy, required this.onAction, required this.onDetails});
  final TechnicianTask task;
  final bool busy;
  final ValueChanged<String> onAction;
  final VoidCallback onDetails;

  @override
  Widget build(BuildContext context) {
    final request = task.request;
    final status = task.requestStatus;
    final date = _dateTime(task.assignment['starts_at'] as String?);
    final address = request['service_address'] as String?;
    String? action;
    String? actionLabel;
    if (task.assignmentStatus == 'OFFERED') { action = 'accept'; actionLabel = 'Принять назначение'; }
    if (task.assignmentStatus == 'ACCEPTED' && status == 'ACCEPTED') { action = 'IN_PROGRESS'; actionLabel = 'Начать работу'; }
    if (task.assignmentStatus == 'ACCEPTED' && status == 'IN_PROGRESS') { action = 'COMPLETED'; actionLabel = 'Завершить работу'; }
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18), side: const BorderSide(color: Color(0xffe4ece9))),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Expanded(child: Text(_statusLabel(status), style: const TextStyle(color: Color(0xff13816f), fontWeight: FontWeight.w700))), const Icon(Icons.chevron_right, color: Colors.blueGrey)]),
          const SizedBox(height: 8),
          Text(request['title'] as String? ?? 'Заявка', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
          if (address != null && address.isNotEmpty) ...[
            const SizedBox(height: 10),
            _InfoLine(icon: Icons.location_on_outlined, text: address),
          ],
          if (date != null) ...[
            const SizedBox(height: 8),
            _InfoLine(icon: Icons.schedule, text: date),
          ],
          const SizedBox(height: 12),
          Row(children: [TextButton.icon(onPressed: onDetails, icon: const Icon(Icons.notes_outlined), label: const Text('Подробности')),
            const Spacer(),
            if (action != null) FilledButton(onPressed: busy ? null : () => onAction(action!), child: busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : Text(actionLabel!)),
          ]),
        ]),
      ),
    );
  }
}

class _TaskDetails extends StatefulWidget {
  const _TaskDetails({required this.api, required this.token, required this.task});
  final FixFlowApi api;
  final String token;
  final TechnicianTask task;

  @override
  State<_TaskDetails> createState() => _TaskDetailsState();
}

class _TaskDetailsState extends State<_TaskDetails> {
  final _note = TextEditingController();
  List<Map<String, dynamic>> _notes = const [];
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() { super.initState(); _loadNotes(); }
  @override
  void dispose() { _note.dispose(); super.dispose(); }

  Future<void> _loadNotes() async {
    try {
      final values = await widget.api.notes(widget.token, widget.task.request['id'] as String);
      if (mounted) setState(() => _notes = values);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _sendNote() async {
    if (_note.text.trim().isEmpty) return;
    setState(() { _saving = true; _error = null; });
    try {
      await widget.api.addNote(widget.token, widget.task.request['id'] as String, _note.text.trim());
      _note.clear();
      await _loadNotes();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final request = widget.task.request;
    final desired = _dateTime(request['desired_visit_at'] as String?);
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(20, 4, 20, MediaQuery.viewInsetsOf(context).bottom + 20),
        child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Text(request['title'] as String? ?? 'Заявка', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 14),
          Text(request['description'] as String? ?? ''),
          if ((request['service_address'] as String? ?? '').isNotEmpty) ...[
            const SizedBox(height: 18),
            _InfoLine(icon: Icons.location_on_outlined, text: request['service_address'] as String),
          ],
          if (desired != null) ...[
            const SizedBox(height: 10),
            _InfoLine(icon: Icons.event_available_outlined, text: 'Желаемое время: $desired'),
          ],
          const SizedBox(height: 22),
          Text('Заметки', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          if (_loading) const LinearProgressIndicator(),
          for (final note in _notes) ListTile(contentPadding: EdgeInsets.zero, leading: const CircleAvatar(child: Icon(Icons.person_outline)), title: Text(note['body'] as String? ?? ''), subtitle: Text(_dateTime(note['created_at'] as String?) ?? '')),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: _ErrorBox(message: _error!)),
          const SizedBox(height: 8),
          Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Expanded(child: TextField(controller: _note, minLines: 1, maxLines: 4, decoration: const InputDecoration(labelText: 'Добавить заметку'))),
            const SizedBox(width: 8),
            IconButton.filled(onPressed: _saving ? null : _sendNote, icon: _saving ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.send)),
          ]),
        ])),
      ),
    );
  }
}

class _Brand extends StatelessWidget {
  const _Brand({this.compact = false});
  final bool compact;
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: compact ? 36 : 48, height: compact ? 36 : 48, decoration: BoxDecoration(color: const Color(0xff168c78), borderRadius: BorderRadius.circular(14)), child: Icon(Icons.handyman_outlined, color: Colors.white, size: compact ? 20 : 26)),
        const SizedBox(width: 10),
        Text('FIXFLOW', style: TextStyle(letterSpacing: 2.1, fontWeight: FontWeight.w900, fontSize: compact ? 16 : 19)),
      ]);
}

class _InfoLine extends StatelessWidget {
  const _InfoLine({required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) => Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Icon(icon, size: 19, color: const Color(0xff168c78)), const SizedBox(width: 8), Expanded(child: Text(text))]);
}

class _ErrorBox extends StatelessWidget {
  const _ErrorBox({required this.message});
  final String message;
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: const Color(0xffffeeee), borderRadius: BorderRadius.circular(12)), child: Text(message, style: const TextStyle(color: Color(0xffa43333))));
}

class _EmptyTasks extends StatelessWidget {
  const _EmptyTasks();
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.symmetric(vertical: 56), child: Column(children: [const Icon(Icons.event_available_outlined, size: 52, color: Color(0xff91aaa4)), const SizedBox(height: 12), Text('Пока нет назначенных заявок', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)), const SizedBox(height: 6), const Text('Потяните экран вниз, чтобы обновить список.', textAlign: TextAlign.center, style: TextStyle(color: Colors.blueGrey))]));
}

String? _dateTime(String? value) {
  if (value == null) return null;
  final parsed = DateTime.tryParse(value)?.toLocal();
  if (parsed == null) return null;
  final date = '${parsed.day.toString().padLeft(2, '0')}.${parsed.month.toString().padLeft(2, '0')}.${parsed.year}';
  final time = '${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}';
  return '$date · $time';
}
