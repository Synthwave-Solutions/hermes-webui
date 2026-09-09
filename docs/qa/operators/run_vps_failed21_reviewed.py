"""Bounded Linux qualification replay. No checkout, deployment, or production action.

Run only as the MainPID of the exact independent QA user unit named below.
The selected titles are copied from a hash-bound historical failure receipt.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

WEB_HEAD = '7b2620b3ac40956496bb014d25392d40d95fa5bd'
ENGINE_HEAD = 'b0aaa74f9dcfe9e7caa4692656b4535ce04104e1'
WEB_SOURCE = 'c2181bdce76363ec895680f328687485d177bdd6e119e040ca48f0672e537244'
ENGINE_SOURCE = '653c3f66da11449a366b3ecaa5463306d0e5865456883d6fce205be738c82bf7'
PRIOR_RECEIPT_SHA = '386f2a0524232b38126868510d7984cdfbb841037d912f0873506fdf531a9bc7'
PRIOR_RUN = '20260909-120039-662326096'
PRIOR_RESULTS_SHA = 'be33ee5a2046a8dabb2e1bb0e4a916be7901e8631ad815dfd185490f6322f221'
QA_ROOT = Path('/home/synthwavehq/work/synthpulse-qa-20260909-v1')
UNIT = 'synthpulse-qa-failed21-20260909-v1.service'
REPLAY_NAME = 'replay-failed21-7b2620b3-v1'
PUBLIC = Path('/home/synthwavehq/work/synthpulse/qa-linux-failed21-replay-20260909-v1.json')
FAILED_CASES = [{'file': 'additional-affordances.spec.ts',
  'title': 'US-SP-AFFORDANCE-MESSAGE-FORK selected message creates an exact persistent prefix and child '
           'continuation leaves the private parent unchanged'},
 {'file': 'chat-lifecycle.spec.ts',
  'title': 'US-SP-CHAT-008 explicit interrupt cancels first response and starts requested next message'},
 {'file': 'composer-content.spec.ts',
  'title': 'US-SP-CHAT-PROMPTS saved prompt validates empty input saves reloads inserts exact text and '
           'deletes'},
 {'file': 'deep-workflows.spec.ts',
  'title': 'US-SP-SESS-SPLIT all split counts create real independent frames and exit'},
 {'file': 'governance-field-roundtrip.spec.ts',
  'title': 'US-SP-GOV-006 [field removal] clearing all extra grants and denials removes persisted entries'},
 {'file': 'governance-revocation.spec.ts',
  'title': 'US-SP-POL-REVOKE-LEVELS user elevated and admin choices persist while only explicit admin can '
           'administer policy'},
 {'file': 'governance-revocation.spec.ts',
  'title': 'US-SP-GOV-REQUESTER-STATUS retained requester sees pending approved rejected while another '
           'account cannot read or decide those requests'},
 {'file': 'kanban-administration.spec.ts',
  'title': 'US-SP-KAN-ADMIN-DEPENDENCIES add remove reject cycles and guard direct completion until parent '
           'finishes'},
 {'file': 'realtime-voice.spec.ts',
  'title': 'US-SP-VOICE-REALTIME-CONTROLS microphone, push to talk, interruption and session change release '
           'capture correctly'},
 {'file': 'realtime-voice.spec.ts',
  'title': 'US-SP-VOICE-REALTIME-MIC-DENIED microphone refusal fails without creating a provider call'},
 {'file': 'realtime-voice.spec.ts',
  'title': 'US-SP-VOICE-REALTIME-REMOTE-END removed server call stops browser microphone capture'},
 {'file': 'realtime-voice.spec.ts',
  'title': 'US-SP-VOICE-REALTIME-LAUNCH-RACE canceled capability response cannot release a newer pending '
           'launch'},
 {'file': 'session-activation-races.spec.ts',
  'title': 'SUPPLEMENT SESSION ACTIVATION newer New Chat survives a delayed inaccessible saved-session '
           'restore'},
 {'file': 'session-discovery-share.spec.ts',
  'title': 'US-SP-SESS-SHARE-AUTH a readable group participant cannot publish or revoke its owners snapshot'},
 {'file': 'session-import-authority.spec.ts',
  'title': 'US-SP-SESS-IMPORT-AUTHORITY JSON chooser rejects unauthorized workspace before creating a '
           'session and allowed import ignores forged identity'},
 {'file': 'supplement-project-knowledge.spec.ts',
  'title': 'SUPPLEMENT PROJECT KNOWLEDGE retained project pages lose files conversation creation and chat '
           'access after membership removal'},
 {'file': 'supplement-transcript-files.spec.ts',
  'title': 'SUPPLEMENT TRANSCRIPT FILES virtualized long history supports Start outline and End without '
           'losing or duplicating turns'},
 {'file': 'supplement-transcript-files.spec.ts',
  'title': 'SUPPLEMENT TRANSCRIPT FILES CSV table and valid or malformed JSON preserve literal content and '
           'exact downloads'},
 {'file': 'supplement-transcript-files.spec.ts',
  'title': 'SUPPLEMENT TRANSCRIPT FILES HTML preview runs inside an opaque sandbox and cannot read parent '
           'identity or cookies'},
 {'file': 'supplement-transcript-files.spec.ts',
  'title': 'SUPPLEMENT TRANSCRIPT FILES large Markdown falls back to literal text then explicit render is '
           'scoped to the current file'},
 {'file': 'workspace-governance.spec.ts',
  'title': 'US-SP-WS-REVOKE removing workspace membership blocks retained session file reads and fresh '
           'activation despite role ceiling'}]


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def selection_grep(cases):
    # Playwright greps the full project/file/suite/title string, so anchor the
    # complete literal title at its final boundary. Escape only JS regex syntax.
    def escape(text):
        return re.sub(r'([\\^$.*+?()\[\]{}|])', r'\\\1', text)
    require(len(cases) == 21 and len({c['title'] for c in cases}) == 21, 'selection_not_exact21')
    return r'(?:^| )(?:' + '|'.join(escape(c['title']) for c in cases) + ')$'


def scenario_rows(report):
    rows = []
    def visit(suite):
        for spec in suite.get('specs', []):
            for test in spec.get('tests', []):
                rows.append({'file': Path(spec['file']).name, 'title': spec['title'],
                             'test_id': spec['id'], 'status': test.get('status'),
                             'expected_status': test.get('expectedStatus'),
                             'attempts': test.get('results', [])})
        for child in suite.get('suites', []):
            visit(child)
    for suite in report.get('suites', []):
        visit(suite)
    return rows


def require_selection(report, cases=FAILED_CASES, *, allow_report_errors=False):
    rows = scenario_rows(report)
    expected = {(c['file'], c['title']) for c in cases}
    require(len(rows) == len(expected) == 21, 'catalog_count_mismatch')
    require({(r['file'], r['title']) for r in rows} == expected, 'catalog_title_mismatch')
    require(len({r['test_id'] for r in rows}) == 21, 'duplicate_test_identity')
    require(allow_report_errors or not report.get('errors'), 'report_global_errors')
    return rows


def browser_error_count(attempt, run):
    entries = [a for a in attempt.get('attachments', []) if a.get('name') == 'uncaught-browser-errors']
    require(len(entries) == 1, 'missing_or_duplicate_browser_error_collection')
    entry = entries[0]
    if entry.get('body'):
        raw = base64.b64decode(entry['body'], validate=True)
    else:
        path = Path(entry['path'])
        require(not path.is_symlink() and path.resolve().is_relative_to((run/'results/artifacts').resolve()), 'error_attachment_escape')
        raw = path.read_bytes()
    require(len(raw) < 2_000_000, 'error_attachment_oversize')
    errors = json.loads(raw)
    require(isinstance(errors, list), 'invalid_error_collection')
    return len(errors)


def process_rows(cgroup):
    rows = {}
    for item in Path('/proc').iterdir():
        if not item.name.isdigit() or int(item.name) == os.getpid():
            continue
        try:
            if item.stat().st_uid != 1000 or (item/'cgroup').read_text().strip() != cgroup:
                continue
            raw = (item/'stat').read_text(); fields = raw[raw.rfind(')')+2:].split()
            row = {'pid': int(item.name), 'start_ticks': int(fields[19]),
                   'ppid': int(fields[1]), 'state': fields[0]}
            rows[(row['pid'], row['start_ticks'])] = row
        except (FileNotFoundError, ProcessLookupError):
            continue
    return rows


def still_alive(row):
    try:
        raw = (Path('/proc')/str(row['pid'])/'stat').read_text()
        fields = raw[raw.rfind(')')+2:].split()
        return int(fields[19]) == row['start_ticks'] and fields[0] != 'Z'
    except (FileNotFoundError, ProcessLookupError):
        return False


def atomic_json(path, data):
    # Only summary metadata is published; logs, cookies, transcript, screenshots,
    # provider traffic and raw Playwright reports stay inside the private replay.
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.qa-replay-', delete=False) as handle:
        name = Path(handle.name)
        try:
            json.dump(data, handle, indent=2); handle.write('\n'); handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            name.unlink(missing_ok=True)
            raise
    os.replace(name, path)


def main():
    require(sys.platform == 'linux' and socket.gethostname() == 'synthwave-vps', 'wrong_host')
    require(os.getuid() == 1000 and pwd.getpwuid(1000).pw_name == 'synthwavehq', 'wrong_identity')
    os.umask(0o077); sys.dont_write_bytecode = True
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    require(QA_ROOT.resolve() == QA_ROOT and QA_ROOT.stat().st_uid == 1000, 'qa_root_untrusted')
    web, engine = QA_ROOT/'webui', QA_ROOT/'engine'
    require(all(p.resolve() == p and p.stat().st_uid == 1000 for p in (web, engine)), 'qa_checkout_untrusted')
    require(not Path('/etc/hermes').exists(), 'managed_env_present')
    require(not any((p/n).exists() for p in (web, engine) for n in ('.env', '.env.local')), 'checkout_env_present')
    require(shutil.disk_usage(QA_ROOT).free > 2*1024**3, 'insufficient_start_disk')
    cgroup = Path('/proc/self/cgroup').read_text().strip()
    require(cgroup.startswith('0::/') and cgroup.split('/')[-1] == UNIT, 'wrong_unit_cgroup')
    cgpath = Path('/sys/fs/cgroup')/cgroup.split('::', 1)[1].lstrip('/')
    quota, period = (cgpath/'cpu.max').read_text().split()
    require(quota.isdigit() and int(quota) == 4*int(period), 'qa_cpu_quota_not400percent')
    require((cgpath/'memory.max').read_text().strip() == str(4*1024**3), 'qa_memory_limit_mismatch')
    identity_env = {'PATH': '/usr/bin:/bin', 'XDG_RUNTIME_DIR': '/run/user/1000'}
    main_pid = subprocess.check_output(['systemctl', '--user', 'show', UNIT, '-p', 'MainPID', '--value'], env=identity_env, text=True, timeout=10).strip()
    require(main_pid == str(os.getpid()), 'operator_not_unit_mainpid')
    require(PUBLIC.parent.resolve() == PUBLIC.parent and PUBLIC.parent.stat().st_uid == 1000, 'publication_parent_untrusted')
    require(not PUBLIC.exists() and not PUBLIC.is_symlink(), 'publication_already_exists')
    replay = QA_ROOT/REPLAY_NAME
    require(not replay.exists() and not replay.is_symlink(), 'replay_already_exists')
    sys.path.insert(0, str(web/'scripts/e2e'))
    from run_full import provenance
    before = {'webui': provenance(web), 'engine': provenance(engine)}
    expected = {'webui': (WEB_HEAD, WEB_SOURCE), 'engine': (ENGINE_HEAD, ENGINE_SOURCE)}
    for key, (head, source) in expected.items():
        require(before[key]['head'] == head and before[key]['source_sha256'] == source, 'source_pair_mismatch')
        require(before[key]['tracked_diff_sha256'] == sha(b''), 'tracked_checkout_dirty')
    replay.mkdir(mode=0o700)
    for name in ('home', 'tmp', 'runs'):
        (replay/name).mkdir(mode=0o700)
    env = {'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/local/bin:/usr/bin:/bin',
           'HOME': str(replay/'home'), 'TMPDIR': str(replay/'tmp'), 'LANG': 'C.UTF-8',
           'QA_PLAYWRIGHT_CLI': str(QA_ROOT/'e2e-tooling/node_modules/@playwright/test/cli.js'),
           'PLAYWRIGHT_BROWSERS_PATH': str(QA_ROOT/'browser-cache')}
    pattern = selection_grep(FAILED_CASES)
    d = {'kind': 'isolated_linux_exact_failed21_replay', 'status': 'starting',
         'prior_failure_receipt_sha256': PRIOR_RECEIPT_SHA, 'prior_run': PRIOR_RUN,
         'prior_results_sha256': PRIOR_RESULTS_SHA, 'selected_cases': FAILED_CASES,
         'selection_sha256': sha(json.dumps(FAILED_CASES, sort_keys=True, separators=(',', ':')).encode()),
         'operator_sha256': sha(Path(__file__).read_bytes()),
         'source': {k: {n: v[n] for n in ('head', 'source_sha256')} for k, v in before.items()},
         'platform': sys.platform, 'python': sys.version.split()[0], 'unit': UNIT,
         'unit_cgroup': cgroup, 'cpu_quota_percent': 400, 'memory_max_gib': 4,
         'disk_floor_gib': 1.5, 'source_unchanged': False,
         'qualification': 'Scoped fresh-state replay only; does not replace the failed224 full run or prove all Linux features.'}
    def save():
        d['at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        atomic_json(replay/'execution.json', d); atomic_json(PUBLIC, d)
    started = time.monotonic(); known = {}; proc = None
    save()
    try:
        d['stage'] = 'catalog_preflight'; save()
        catalog_auth = replay/'catalog-only.json'
        catalog_auth.write_text(json.dumps({'base_url': 'http://127.0.0.1:19086',
                                           'workspace': str(replay/'catalog-workspace'),
                                           'cookies': {}, 'extension_fixture': {}}))
        catalog_env = {**env, 'QA_SESSIONS': str(catalog_auth), 'QA_BASE_URL': 'http://127.0.0.1:19086',
                       'QA_OUT': str(replay/'catalog-output'),
                       'NODE_PATH': str(Path(env['QA_PLAYWRIGHT_CLI']).resolve().parents[2])}
        listing = subprocess.run(['node', env['QA_PLAYWRIGHT_CLI'], 'test', '-c', 'playwright.full.config.ts',
                                  '--list', '--reporter=json', '--grep', pattern], cwd=web, env=catalog_env,
                                 capture_output=True, timeout=60, check=True)
        catalog = json.loads(listing.stdout); require_selection(catalog)
        require(catalog['config']['workers'] == 1 and all(p['retries'] == 0 for p in catalog['config']['projects']), 'runner_parallel_or_retry_override')
        atomic_json(replay/'catalog.json', catalog)
        d['catalog_count'] = 21; d['catalog_sha256'] = sha((replay/'catalog.json').read_bytes())
        d['playwright'] = subprocess.check_output(['node', env['QA_PLAYWRIGHT_CLI'], '--version'], env=env, text=True, timeout=15).strip()
        d['stage'] = 'browser_execution'; d['status'] = 'running'; save()
        with (replay/'runner.log').open('w') as log:
            proc = subprocess.Popen([str(web/'.venv/bin/python'), '-B', str(web/'scripts/e2e/run_full.py'),
                                     '--engine', str(engine), '--out', str(replay/'runs'), '--grep', pattern],
                                    cwd=web, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            d['runner_pid'] = proc.pid; save()
            while proc.poll() is None:
                known.update(process_rows(cgroup))
                free = shutil.disk_usage(QA_ROOT).free
                d['free_gib'] = round(free/1024**3, 2); d['elapsed_seconds'] = round(time.monotonic()-started, 1)
                raw = (replay/'runner.log').read_text(errors='replace')
                d['reported_passes'] = len(re.findall(r'^\s*\u2713\s+\d+ ', raw, re.M))
                d['reported_failures'] = len(re.findall(r'^\s*[\u2718x]\s+\d+ ', raw, re.M))
                atomic_json(replay/'census-during.json', {'cgroup': cgroup, 'processes': list(known.values())})
                if free < 1.5*1024**3:
                    d['abort_reason'] = 'disk_reserve'; save(); os.killpg(proc.pid, signal.SIGTERM); break
                save(); time.sleep(5)
            code = proc.wait(timeout=45)
        d['runner_exit_code'] = code; d['stage'] = 'result_validation'
        after = {'webui': provenance(web), 'engine': provenance(engine)}
        d['source_unchanged'] = before == after
        runs = list((replay/'runs').iterdir())
        require(len(runs) == 1 and (runs[0]/'run.json').is_file(), 'no_unique_completed_run_manifest')
        run = runs[0]; manifest = json.loads((run/'run.json').read_text())
        report = json.loads((run/'results/results.json').read_text())
        require(manifest['initial_source'] == before and manifest['final_source'] == after, 'manifest_provenance_mismatch')
        require(manifest['source_unchanged_during_run'] is True and d['source_unchanged'], 'source_changed')
        require(manifest['test_exit_code'] == code, 'exit_code_mismatch')
        require(Path(manifest['results']).resolve() == run/'results/results.json' and Path(manifest['engine']).resolve() == engine, 'manifest_path_mismatch')
        d['run_id'] = run.name; d['statistics'] = report.get('stats')
        d['run_manifest_sha256'] = sha((run/'run.json').read_bytes())
        d['results_sha256'] = sha((run/'results/results.json').read_bytes())
        d['report_global_error_count'] = len(report.get('errors', []))
        rows = require_selection(report, allow_report_errors=True)
        d['scenarios'] = []
        for row in rows:
            item = {k: row[k] for k in ('file', 'title', 'test_id', 'status')}
            item['attempts'] = []
            for attempt in row['attempts']:
                entry = {'status': attempt.get('status'), 'duration_ms': attempt.get('duration')}
                try:
                    entry['browser_error_count'] = browser_error_count(attempt, run)
                except (ValueError, KeyError, OSError) as error:
                    entry['browser_error_count'] = None
                    entry['error_collection_unverified'] = type(error).__name__
                item['attempts'].append(entry)
            d['scenarios'].append(item)
        probe = json.loads((run/'e2e-state/runtime-engine.json').read_text())
        require(Path(probe['engine_module']).resolve() == engine/'hermes_cli/kanban_db.py' and probe['guard_installed'] is True, 'engine_child_or_guard_mismatch')
        d['selected_engine_child_verified'] = True
        passed = code == 0 and not d['report_global_error_count'] and report['stats']['expected'] == 21 and all(report['stats'][x] == 0 for x in ('unexpected', 'skipped', 'flaky'))
        passed = passed and all(r['status'] == 'expected' and r['expected_status'] == 'passed' and len(r['attempts']) == 1
                                and r['attempts'][0].get('status') == 'passed' and not r['attempts'][0].get('errors')
                                and browser_error_count(r['attempts'][0], run) == 0 for r in rows)
        d['status'] = 'passed_exact21_pending_post_unit_cleanup' if passed else 'failed'
    except BaseException as error:
        d['status'] = 'failed'; d['failure_class'] = type(error).__name__
        # Record only a controlled classification, never arbitrary log/error text.
        if isinstance(error, ValueError) and re.fullmatch(r'[a-z0-9_]+', str(error)):
            d['failure_code'] = str(error)
    finally:
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM); proc.wait(timeout=45)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                d['own_runner_stop_unconfirmed'] = True
        survivors = []
        try:
            known.update(process_rows(cgroup)); time.sleep(2)
            survivors = [row for row in known.values() if still_alive(row)]
        except OSError as error:
            d['cleanup_inspection_failed'] = type(error).__name__
            d['status'] = 'failed'
        d['sampled_process_identities'] = len(known)
        d['sampled_owned_survivors_before_unit_exit'] = survivors
        d['cleanup_scope'] = 'Exact own-unit cgroup samples and retained PID/start ticks before operator exit; post-unit cgroup and known listener inspection still required. No universal process-history claim.'
        d['elapsed_seconds'] = round(time.monotonic()-started, 1)
        if survivors or d.get('own_runner_stop_unconfirmed'):
            d['status'] = 'failed'
        save()
    return 0 if d['status'] == 'passed_exact21_pending_post_unit_cleanup' else 1


if __name__ == '__main__':
    raise SystemExit(main())
