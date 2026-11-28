[CmdletBinding()]
param(
    [string]$Repository = (Get-Location).Path,
    [string]$Python = 'python',
    [string]$BrokerPython,
    [switch]$InstallDependencies
)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'This suite requires Windows.' }
$revision = '0e761637e4e61bafdccd0d06fe3abedf6225aba4'
$qaBase = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Temp'
$qaRoot = Join-Path $qaBase ('TRADEGEN-Windows-QA-' + [Guid]::NewGuid().ToString('N'))
$qaSource = Join-Path $qaRoot 'source'
$qaProfile = Join-Path $qaRoot 'profile'
$qaLocal = Join-Path $qaProfile 'AppData/Local'
$qaTemp = Join-Path $qaLocal 'Temp'
$qaState = Join-Path $qaProfile 'tradegen-test-state'
$qaReport = Join-Path $qaRoot 'result.json'
$qaBrokerReport = Join-Path $qaRoot 'broker-result.json'
$qaHarness = Join-Path $qaRoot 'cases.py'
foreach ($location in @($qaRoot, $qaSource, $qaProfile, $qaLocal, $qaTemp, $qaState)) {
    [IO.Directory]::CreateDirectory($location) | Out-Null
}
$qaArchive = Join-Path $qaRoot 'source.zip'
& git -C $Repository archive --format=zip "--output=$qaArchive" $revision
if ($LASTEXITCODE -ne 0) { throw 'Fetch the tested commit in this clone before running the suite.' }
Expand-Archive -LiteralPath $qaArchive -DestinationPath $qaSource
if (Test-Path -LiteralPath (Join-Path $qaSource '.env')) { throw 'A clean archive without local configuration is required.' }
$qaInterpreter = (Get-Command $Python -ErrorAction Stop).Source
if ($InstallDependencies) {
    $qaBasePython = $qaInterpreter
    $qaVenv = Join-Path $qaRoot 'venv'
    & $qaInterpreter -I -m venv $qaVenv
    if ($LASTEXITCODE -ne 0) { throw 'A temporary Python 3.13 venv could not be created.' }
    $qaInterpreter = Join-Path $qaVenv 'Scripts/python.exe'
    & $qaInterpreter -I -m pip --isolated install --disable-pip-version-check --no-cache-dir --index-url https://pypi.org/simple -c (Join-Path $qaSource 'constraints.txt') numpy pandas scipy matplotlib PyYAML requests python-dotenv tzdata 'fido2==2.2.1' cryptography websockets
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. No Windows test ran.' }
    $qaBrokerVenv = Join-Path $qaRoot 'broker-venv'
    & $qaBasePython -I -m venv --without-pip $qaBrokerVenv
    if ($LASTEXITCODE -ne 0) { throw 'The temporary broker environment was not created.' }
    $BrokerPython = Join-Path $qaBrokerVenv 'Scripts/python.exe'
    & $qaInterpreter -I -m pip --isolated --python $BrokerPython install --no-compile --disable-pip-version-check --no-cache-dir --index-url https://pypi.org/simple -r (Join-Path $qaSource 'tools/approval_broker/requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'The isolated broker requirements could not be installed.' }
}
if (-not $BrokerPython) { throw 'Supply -InstallDependencies or both -Python and -BrokerPython.' }
$qaBrokerInterpreter = (Get-Command $BrokerPython -ErrorAction Stop).Source
$qaCode = @'
import importlib
import json
import os
import re
import traceback
from pathlib import Path
import socket
import sys

if sys.platform != "win32" or sys.version_info[:2] != (3, 13):
    raise SystemExit("Windows and CPython 3.13 are required")
source = Path(sys.argv[1]).resolve(strict=True)
report_path = Path(sys.argv[2]).resolve()
test_home = Path(sys.argv[3]).resolve(strict=True)
if Path.home().resolve() != test_home or not Path(os.environ["TRADEGEN_HOME"]).resolve().is_relative_to(test_home):
    raise SystemExit("Temporary Windows test home required")
sys.path.insert(0, str(source))
from tests.notrun import NotRun

CASES = {'launch_private_input': ['test_windows_reader_returns_exact_bytes_and_cli_reports_without_echo',
                          'test_windows_reader_refuses_junction_parents_at_any_depth',
                          'test_windows_reader_refuses_file_and_directory_symlinks',
                          'test_windows_reader_refuses_both_names_of_a_hard_link',
                          'test_windows_reader_refuses_short_name_aliases_including_private_roots',
                          'test_windows_reader_refuses_real_streams_and_device_names_before_metadata',
                          'test_windows_reader_bounds_size_with_honest_and_stale_metadata',
                          'test_windows_reader_detects_file_and_parent_swaps_between_check_and_open',
                          'test_windows_reader_refuses_cloud_placeholder_and_offline_attributes',
                          'test_windows_reader_refuses_directories_missing_and_file_parent_paths',
                          'test_windows_clis_keep_strict_duplicate_key_and_oversize_refusals',
                          'test_windows_deployment_manifest_round_trip_matches_owner_and_signer_closure'],
 'launch_workflow': ['test_example_writer_allows_windows_scratch_only_while_temp_lies_under_localappdata'],
 'launch_passkey_owner_release': ['test_release_walk_refuses_a_kelvin_twin_name',
                                  'test_release_walk_refuses_trailing_dot_or_space_names_on_windows',
                                  'test_windows_broker_release_commits_running_interpreter_venv_root_and_native_modules'],
 'compliance_signer': ['test_stdin_terminal_check_follows_getconsolemode'],
 'control_existing_journal': ['test_existing_mode_is_exact_bool_and_invalid_admission_has_no_filesystem_effect',
                              'test_existing_mode_flag_and_property_reject_normal_reassignment_and_deletion',
                              'test_missing_existing_lock_never_recreates_it_or_changes_the_valid_pair',
                              'test_deleted_pair_or_lock_during_transaction_poison_append_without_recreation',
                              'test_deleted_journal_after_load_before_existing_open_is_not_recreated',
                              'test_existing_only_append_matches_legacy_exact_journal_and_checkpoint_bytes',
                              'test_lock_release_failure_does_not_revive_transaction_or_rollback_durable_row',
                              'test_truncated_earlier_valid_prefix_remains_blocked_by_existing_checkpoint']}
def refuse(event, args):
    if event in {"socket.connect", "socket.sendto", "socket.getaddrinfo", "socket.bind", "socket.gethostbyname"}:
        raise RuntimeError("NETWORK_FORBIDDEN")
sys.addaudithook(refuse)
broker_case = "test_windows_broker_release_commits_running_interpreter_venv_root_and_native_modules"
is_broker = sys.argv[4] == "broker"
if not is_broker:
    from tests.control_acceptance import _wrap
rows = []
for module, cases in CASES.items():
    for case in cases:
        if (case == broker_case) != is_broker:
            continue
        label = module + "/" + case
        try:
            fn = getattr(importlib.import_module("tests." + module), case)
            if is_broker:
                fn()
            else:
                _wrap(fn)()
            row = {"case": label, "status": "PASS"}
        except NotRun as error:
            row = {"case": label, "status": "NOT_RUN", "reason": str(error)}
        except Exception as error:
            # Logs contain case identifiers and exception types, never file contents or local paths.
            row = {"case": label, "status": "FAIL", "exception": type(error).__name__}
            if re.fullmatch("[A-Z][A-Z0-9_]{1,80}", str(error)):
                row["reason"] = str(error)
            trace = [f for f in traceback.extract_tb(error.__traceback__) if Path(f.filename).is_relative_to(source)]
            if trace:
                row["site"] = Path(trace[-1].filename).relative_to(source).as_posix() + "#" + str(trace[-1].lineno)
        rows.append(row)
        print(row["status"], label, row.get("exception", ""), row.get("reason", ""), row.get("site", ""), flush=True)
counts = {s: sum(r["status"] == s for r in rows) for s in ("PASS", "FAIL", "NOT_RUN")}
if len(rows) != (1 if is_broker else sum(map(len, CASES.values())) - 1):
    raise SystemExit("Incomplete case enumeration")
report = {"group": sys.argv[4], "source": "0e761637e4e61bafdccd0d06fe3abedf6225aba4", "platform": sys.platform,
          "python": sys.version.split()[0], "counts": counts, "cases": rows}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2) + "\n",encoding="utf-8")
print(json.dumps(counts), flush=True)
raise SystemExit(1 if counts["FAIL"] or counts["NOT_RUN"] else 0)
'@
[IO.File]::WriteAllText($qaHarness, $qaCode, [Text.UTF8Encoding]::new($false))
$qaProcess = [Diagnostics.ProcessStartInfo]::new()
$qaProcess.FileName = $qaInterpreter
$qaProcess.UseShellExecute = $false
$qaProcess.WorkingDirectory = $qaSource
$qaProcess.EnvironmentVariables.Clear()
foreach ($name in @('SystemRoot','SystemDrive','ComSpec','PATH','PATHEXT','PROCESSOR_ARCHITECTURE','NUMBER_OF_PROCESSORS')) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($value) { $qaProcess.EnvironmentVariables[$name] = $value }
}
$qaProcess.EnvironmentVariables['USERPROFILE'] = $qaProfile
$qaProcess.EnvironmentVariables['LOCALAPPDATA'] = $qaLocal
$qaProcess.EnvironmentVariables['APPDATA'] = Join-Path $qaProfile 'AppData/Roaming'
$qaProcess.EnvironmentVariables['TEMP'] = $qaTemp
$qaProcess.EnvironmentVariables['TMP'] = $qaTemp
$qaProcess.EnvironmentVariables['TRADEGEN_HOME'] = $qaState
$qaProcess.EnvironmentVariables['MPLCONFIGDIR'] = Join-Path $qaTemp 'mpl'
$qaProcess.EnvironmentVariables['OPENBLAS_NUM_THREADS'] = '1'
# Windows file names cannot contain double quotes. Only generated local paths are passed.
$failed = $false
foreach ($target in @(@('application', $qaInterpreter, $qaReport), @('broker', $qaBrokerInterpreter, $qaBrokerReport))) {
    $qaProcess.FileName = $target[1]
    $qaProcess.Arguments = '-I -B -X utf8 "' + $qaHarness + '" "' + $qaSource + '" "' + $target[2] + '" "' + $qaProfile + '" ' + $target[0]
    $run = [Diagnostics.Process]::Start($qaProcess)
    $run.WaitForExit()
    Write-Output ('QA_REPORT=' + $target[2])
    if ($run.ExitCode -ne 0) { $failed = $true }
}
if ($failed) { exit 1 }
exit 0
