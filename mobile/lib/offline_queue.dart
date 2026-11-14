import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';
import 'package:uuid/uuid.dart';

/// Durable local command queue. The server must honor each command's idempotency key.
class OfflineQueue {
  Database? _database;

  Future<Database> open() async {
    if (_database != null) return _database!;
    final directory = await getApplicationDocumentsDirectory();
    _database = await openDatabase(p.join(directory.path, 'fixflow.db'), version: 1,
        onCreate: (db, _) async {
      await db.execute('''CREATE TABLE pending_commands (
        id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL,
        last_error TEXT)''');
      await db.execute('CREATE TABLE cached_requests (id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)');
    });
    return _database!;
  }

  Future<String> enqueue(String kind, Map<String, Object?> payload) async {
    final db = await open();
    final id = const Uuid().v4();
    await db.insert('pending_commands', {
      'id': id,
      'kind': kind,
      'payload': jsonEncode(payload),
      'created_at': DateTime.now().toUtc().toIso8601String(),
    });
    return id;
  }

  Future<List<Map<String, Object?>>> pending() async =>
      (await (await open()).query('pending_commands', where: "state = 'pending'", orderBy: 'created_at'));

  Future<void> markConflict(String id, String message) async => (await open()).update(
        'pending_commands', {'state': 'conflict', 'last_error': message}, where: 'id = ?', whereArgs: [id]);

  Future<void> markSynced(String id) async =>
      (await open()).delete('pending_commands', where: 'id = ?', whereArgs: [id]);
}
