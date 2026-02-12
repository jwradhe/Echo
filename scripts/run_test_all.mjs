/* global process */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const root = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';
const venvPython = isWin
  ? path.join(root, '.venv', 'Scripts', 'python.exe')
  : path.join(root, '.venv', 'bin', 'python');

const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python';
const scriptPath = path.join(root, 'scripts', 'run_test_all.py');

const result = spawnSync(pythonCmd, [scriptPath], {
  stdio: 'inherit',
  cwd: root,
});

process.exit(result.status ?? 1);
