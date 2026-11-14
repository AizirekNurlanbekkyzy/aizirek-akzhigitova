import 'package:flutter/material.dart';

void main() => runApp(const FixFlowApp());

class FixFlowApp extends StatelessWidget {
  const FixFlowApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'FixFlow',
        theme: ThemeData(colorSchemeSeed: const Color(0xff087e78), useMaterial3: true),
        home: const TechnicianHome(),
      );
}

class TechnicianHome extends StatelessWidget {
  const TechnicianHome({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('FixFlow · Задания')),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              'Экран техника подключается к API и локальной очереди синхронизации. '
              'Для входа и загрузки заданий требуется настроенный сервер.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
}
