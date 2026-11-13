"""Private archive review packets and current owner authentication, never trading.

Exports copy exact archived bytes to an explicit empty directory. Only generated
logical names become paths. A packet, request or authenticated archival identity
is not source review, strategy selection, activation or recovery authorization.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import ntpath
import re
import os
from pathlib import Path
import stat
import sys

from core.compliance import owner
from core.isolation import checked_target, state_root
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_attestation as A
from execution_launch import research_bundle_format as F
from execution_launch.bundle_auth import authenticate_bundle_attestation
from execution_launch.research_bundle import _code, _read_snapshot, _safe_path, open_explicit_store
from execution_launch.research_bundle_store import BundleStore
from execution_launch.private_input import _REFUSED_ATTRIBUTES

_REPO = Path(__file__).resolve().parents[1]


class BundleReviewError(ValueError):
    """Fixed codes; never original names, private bytes, paths or key information."""


def _need(ok, code):
    if not ok:
        raise BundleReviewError(code)


# Native directory pins deny write/delete sharing; no permissive fallback.
# Linux fake API tests establish the call contract, not native Windows behavior.
class WindowsPinError(ValueError):
    """Fixed code; never an OS message, path, or private file data."""


_WIN_CODE = "BUNDLE_PACKET_WINDOWS_PIN_REFUSED"
_WIN_UNSUPPORTED = "BUNDLE_PACKET_WINDOWS_PIN_UNSUPPORTED"
_WIN_DRIVE = re.compile(r"[A-Za-z]:")
_WIN_DIRECTORY = 0x10
_WIN_REFUSED_ATTRIBUTES = 0x400 | 0x1000 | 0x00040000 | 0x00400000
_WIN_MAX_CHARS = 32767


def _win_need(condition, code=_WIN_CODE):
    if not condition:
        raise WindowsPinError(code)


def _windows_lexical_path(value):
    _win_need(hasattr(ntpath, "splitroot") and hasattr(ntpath, "isreserved"), _WIN_UNSUPPORTED)
    _win_need(type(value) is str and 0 < len(value) <= _WIN_MAX_CHARS and "\x00" not in value)
    # Keep DOS/UNC/device namespaces and drive-relative paths out of this API.
    normalized = value.replace("/", "\\")
    drive, root, tail = ntpath.splitroot(normalized)
    _win_need(_WIN_DRIVE.fullmatch(drive) is not None and root == "\\")
    parts = tail.split("\\") if tail else []
    _win_need(all(part and part not in (".", "..") and not ntpath.isreserved(part) for part in parts))
    return drive.upper() + root + "\\".join(parts)


def _windows_final_path(value):
    _win_need(type(value) is str and value.startswith("\\\\?\\"))
    # UNC/device/volume-GUID output cannot pass the letter-drive lexical check.
    return _windows_lexical_path(value[4:])


@dataclass(frozen=True, kw_only=True)
class DirectoryInformation:
    attributes: int
    volume_serial: int
    file_index: int

    @property
    def identity(self):
        _win_need(type(self.attributes) is int and self.attributes >= 0
              and self.attributes & _WIN_DIRECTORY
              and not self.attributes & _WIN_REFUSED_ATTRIBUTES)
        _win_need(type(self.volume_serial) is int and 0 <= self.volume_serial < 2**32
              and type(self.file_index) is int and 0 < self.file_index < 2**64)
        return self.volume_serial, self.file_index


class NativeDirectoryAPI:
    """Small injectable seam; fake APIs must emulate these four methods.

    The object is created only for the explicit Windows operation. No Windows
    DLL is loaded by importing this module, and no app module is imported here.
    """
    def __init__(self):
        _win_need(os.name == "nt", _WIN_UNSUPPORTED)
        import ctypes
        from ctypes import wintypes

        class FileTime(ctypes.Structure):
            _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

        class HandleInformation(ctypes.Structure):
            _fields_ = [("attributes", wintypes.DWORD), ("created", FileTime),
                ("accessed", FileTime), ("written", FileTime), ("volume", wintypes.DWORD),
                ("size_high", wintypes.DWORD), ("size_low", wintypes.DWORD),
                ("links", wintypes.DWORD), ("index_high", wintypes.DWORD),
                ("index_low", wintypes.DWORD)]

        self._ctypes, self._info_type = ctypes, HandleInformation
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self._kernel.CreateFileW.restype = wintypes.HANDLE
        self._kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(HandleInformation)]
        self._kernel.GetFileInformationByHandle.restype = wintypes.BOOL
        self._kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
            wintypes.DWORD, wintypes.DWORD]
        self._kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.CloseHandle.restype = wintypes.BOOL

    def open_directory(self, path):
        # FILE_READ_ATTRIBUTES; FILE_SHARE_READ only; OPEN_EXISTING;
        # FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT.
        handle = self._kernel.CreateFileW(path, 0x80, 0x1, None, 3, 0x02000000 | 0x00200000, None)
        _win_need(handle is not None and handle != self._ctypes.c_void_p(-1).value)
        return handle

    def information(self, handle):
        info = self._info_type()
        _win_need(bool(self._kernel.GetFileInformationByHandle(handle, self._ctypes.byref(info))))
        return DirectoryInformation(attributes=int(info.attributes), volume_serial=int(info.volume),
            file_index=(int(info.index_high) << 32) | int(info.index_low))

    def final_path(self, handle):
        buffer = self._ctypes.create_unicode_buffer(_WIN_MAX_CHARS + 2)
        size = self._kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        _win_need(0 < size < len(buffer))
        return buffer.value

    def close(self, handle):
        _win_need(bool(self._kernel.CloseHandle(handle)))


class WindowsDirectoryPin:
    def __init__(self, api, rows):
        self._api, self._rows, self._closed = api, tuple(rows), False
        self.root_handle = rows[-1][1]
        self.identity = rows[-1][2]
        self.path = rows[-1][0]

    def check(self):
        _win_need(not self._closed)
        for path, handle, identity in self._rows:
            current = self._api.information(handle)
            _win_need(type(current) is DirectoryInformation and current.identity == identity)
            _win_need(ntpath.normcase(_windows_final_path(self._api.final_path(handle))) == ntpath.normcase(path))


@contextmanager
def _held_windows_directory(path, *, api=None):
    """Retain every native ancestor/root handle, or refuse without weaker fallback.

    `api` is a dependency-injection seam for hermetic contract tests, never a
    serialized input or an application-controlled trust flag.
    """
    path = _windows_lexical_path(path)
    try:
        native = NativeDirectoryAPI() if api is None else api
    except WindowsPinError:
        raise
    except (OSError, AttributeError, TypeError, RuntimeError):
        raise WindowsPinError(_WIN_UNSUPPORTED) from None
    rows, handles, pin = [], [], None
    drive, root, tail = ntpath.splitroot(path)
    prefixes = [drive + root]
    for part in tail.split("\\") if tail else ():
        prefixes.append(ntpath.join(prefixes[-1], part))
    try:
        for prefix in prefixes:
            handle = native.open_directory(prefix)
            handles.append(handle)  # Close even when the next identity check fails.
            info = native.information(handle)
            _win_need(type(info) is DirectoryInformation)
            identity = info.identity
            _win_need(ntpath.normcase(_windows_final_path(native.final_path(handle))) == ntpath.normcase(prefix))
            rows.append((prefix, handle, identity))
        pin = WindowsDirectoryPin(native, rows)
        pin.check()
        try:
            yield pin
        finally:
            pin.check()  # The caller's publication must not outlive these pins.
    except WindowsPinError:
        raise
    except (OSError, ValueError, TypeError, AttributeError, RuntimeError, OverflowError):
        raise WindowsPinError(_WIN_CODE) from None
    finally:
        if pin is not None:
            pin._closed = True
        close_failed = False
        for handle in reversed(handles):
            try:
                native.close(handle)
            except Exception:
                # Continue closing all acquired handles; never leak later ones
                # merely because one native close reported failure.
                close_failed = True
        if close_failed:
            raise WindowsPinError(_WIN_CODE) from None


class _WindowsPinContext:
    """I/O-free construction; native pins exist only between enter and exit."""
    def __init__(self, path, *, api=None):
        self._context = _held_windows_directory(path, api=api)
        self._pin = None
        self._used = False

    def __enter__(self):
        _win_need(not self._used)
        self._used = True
        self._pin = self._context.__enter__()
        return self

    def check(self):
        _win_need(self._pin is not None)
        self._pin.check()

    @property
    def root_handle(self):
        self.check()
        return self._pin.root_handle

    @property
    def identity(self):
        self.check()
        return self._pin.identity

    @property
    def path(self):
        self.check()
        return self._pin.path

    def __exit__(self, exc_type, exc, traceback):
        _win_need(self._pin is not None)
        try:
            return self._context.__exit__(exc_type, exc, traceback)
        finally:
            self._pin = None


def pin_windows_directory(path, *, api=None):
    """Return an I/O-free context manager exposing enter/check/exit and root identity."""
    return _WindowsPinContext(path, api=api)


def _identity(info):
    _need(info.st_ino > 0, 'BUNDLE_REVIEW_IDENTITY_UNAVAILABLE')
    return info.st_dev, info.st_ino


def _file_identity(info):
    return _identity(info) + (info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _directory(path):
    info = os.lstat(path)
    _need(stat.S_ISDIR(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & _REFUSED_ATTRIBUTES,
          'BUNDLE_REVIEW_PATH_REFUSED')
    return _identity(info)


def _file(info, maximum):
    _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 <= info.st_size <= maximum
          and not getattr(info, 'st_file_attributes', 0) & _REFUSED_ATTRIBUTES,
          'BUNDLE_REVIEW_FILE_REFUSED')
    return _file_identity(info)


def _checked_output(path, store):
    _safe_path(path)
    _need(os.path.normcase(str(path)) == os.path.normcase(os.path.realpath(path, strict=True)),
          'BUNDLE_REVIEW_PATH_REFUSED')
    for prefix in (path, *path.parents):
        _directory(prefix)
    # Neither an immutable store nor an owner/repository tree is a packet destination.
    # The state path check is the same trusted isolation boundary used by BundleStore.
    for other in (store.roots.sealed_root, store.roots.backup_root, _REPO, state_root().absolute().resolve()):
        _need(not path.is_relative_to(other) and not other.is_relative_to(path), 'BUNDLE_REVIEW_OUTPUT_NOT_SEPARATE')
    checked_target(path, 'archive review output')
    return path


def _names(path, descriptor, maximum):
    names = []
    with os.scandir(path if descriptor is None else descriptor) as entries:
        for entry in entries:
            _need(len(names) < maximum, 'BUNDLE_REVIEW_RESOURCE_LIMIT')
            names.append(entry.name)
    return frozenset(names)


def _open_posix_directory(path):
    descriptor = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
        descriptor = os.open(path.anchor, flags)
        for component in path.parts[1:]:
            following = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        _need(_identity(os.fstat(descriptor)) == _directory(path), 'BUNDLE_REVIEW_DIRECTORY_CHANGED')
        return descriptor
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        raise


class _PacketOutput:
    """Pinned destination handles survive until complete exact readback finishes."""
    def __init__(self, path, store):
        self.root = _checked_output(path, store)
        self.payloads = self.root/'payloads'
        self.root_fd = self.payload_fd = None
        self.root_pin = self.payload_pin = None
        self.root_identity = self.payload_identity = None

    def __enter__(self):
        try:
            if os.name == 'nt':
                pin = pin_windows_directory(str(self.root))
                pin.__enter__()
                self.root_pin = pin
            else:
                _need(hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'), 'BUNDLE_REVIEW_PLATFORM_UNSUPPORTED')
                self.root_fd = _open_posix_directory(self.root)
            self.root_identity = _directory(self.root)
            self.check()
            with os.scandir(self.root if self.root_fd is None else self.root_fd) as entries:
                _need(next(entries, None) is None, 'BUNDLE_REVIEW_OUTPUT_EXISTS')
            self._make_payload_directory()
            return self
        except BaseException:
            self._close()
            raise

    def _make_payload_directory(self):
        self.check()
        checked_target(self.payloads, 'archive review payload directory', within=self.root)
        if self.root_fd is None:
            os.mkdir(self.payloads, 0o700)
            pin = pin_windows_directory(str(self.payloads))
            pin.__enter__()
            self.payload_pin = pin
        else:
            os.mkdir('payloads', 0o700, dir_fd=self.root_fd)
            self.payload_fd = os.open('payloads', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                                     | getattr(os, 'O_CLOEXEC', 0), dir_fd=self.root_fd)
        self.payload_identity = _directory(self.payloads)
        self.check()
        self.sync()

    def check(self):
        _need(_directory(self.root) == self.root_identity, 'BUNDLE_REVIEW_DIRECTORY_CHANGED')
        if self.root_fd is not None:
            _need(_identity(os.fstat(self.root_fd)) == self.root_identity, 'BUNDLE_REVIEW_DIRECTORY_CHANGED')
        if self.root_pin is not None:
            self.root_pin.check()
        if self.payload_identity is not None:
            _need(_directory(self.payloads) == self.payload_identity, 'BUNDLE_REVIEW_DIRECTORY_CHANGED')
            if self.payload_fd is not None:
                _need(_identity(os.fstat(self.payload_fd)) == self.payload_identity,
                      'BUNDLE_REVIEW_DIRECTORY_CHANGED')
            if self.payload_pin is not None:
                self.payload_pin.check()

    def sync(self):
        self.check()
        # fsync a POSIX directory. Win32 directory handles remain pinned but we
        # do not claim FlushFileBuffers-on-directory or power-loss durability.
        for descriptor in (self.payload_fd, self.root_fd):
            if descriptor is not None:
                os.fsync(descriptor)

    def _close(self):
        failed = False
        for name in ('payload_fd', 'root_fd'):
            descriptor = getattr(self, name)
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    failed = True
                finally:
                    setattr(self, name, None)
        for name in ('payload_pin', 'root_pin'):
            pin = getattr(self, name)
            if pin is not None:
                try:
                    pin.__exit__(None, None, None)
                except (ValueError, OSError):
                    failed = True
                finally:
                    setattr(self, name, None)
        _need(not failed, 'BUNDLE_REVIEW_HANDLE_CLOSE_REFUSED')

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                self.check()
        finally:
            self._close()

    def location(self, payload):
        return (self.payloads, self.payload_fd) if payload else (self.root, self.root_fd)


def _write_new(packet, name, raw, *, payload):
    _need(type(raw) is bytes and type(name) is str
          and (name == 'request.json' if not payload else name.startswith('p-') and name.endswith('.bin')
               and A.payload_filename(name[2:-4]) == name), 'BUNDLE_REVIEW_GENERATED_NAME_REQUIRED')
    packet.check()
    directory, directory_fd = packet.location(payload)
    target = checked_target(directory/name, 'archive review packet file', within=directory)
    descriptor = None
    try:
        descriptor = os.open(target if directory_fd is None else name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
            | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOINHERIT', 0) | getattr(os, 'O_CLOEXEC', 0),
            0o600, **({} if directory_fd is None else {'dir_fd': directory_fd}))
        before = os.fstat(descriptor)
        _file(before, 0)
        _need(before.st_size == 0, 'BUNDLE_REVIEW_FILE_CHANGED')
        handle = os.fdopen(descriptor, 'wb')
        descriptor = None
        with handle:
            written = handle.write(raw)
            _need(written == len(raw), 'BUNDLE_REVIEW_SHORT_WRITE')
            handle.flush()
            os.fsync(handle.fileno())
            after = os.fstat(handle.fileno())
            _need(_identity(after) == _identity(before) and after.st_size == len(raw), 'BUNDLE_REVIEW_FILE_CHANGED')
        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False) if directory_fd is not None else os.lstat(target)
        current_identity = _file(current, len(raw))
        # Windows may finalize last-write timestamps when the writing handle
        # closes. Pin the same inode/length, then bind post-close metadata and
        # exact bytes through the independent readback below.
        _need(_identity(current) == _identity(after) and current.st_size == len(raw), 'BUNDLE_REVIEW_FILE_CHANGED')
        packet.check()
        return current_identity
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_back(packet, name, expected, identity, *, payload):
    packet.check()
    directory, directory_fd = packet.location(payload)
    target = directory/name
    if directory_fd is None:
        raw, status = _read_snapshot(target, len(expected))
        _need(status == 'COLLECTED' and raw == expected and _file_identity(os.lstat(target)) == identity,
              'BUNDLE_REVIEW_READBACK_FAILED')
    else:
        descriptor = None
        try:
            before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            _need(_file(before, len(expected)) == identity, 'BUNDLE_REVIEW_FILE_CHANGED')
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0)
                                 | getattr(os, 'O_CLOEXEC', 0), dir_fd=directory_fd)
            _need(_file(os.fstat(descriptor), len(expected)) == identity, 'BUNDLE_REVIEW_FILE_CHANGED')
            chunks, remaining = [], len(expected)+1
            while remaining:
                chunk = os.read(descriptor, min(remaining, 65536))
                if not chunk:
                    break
                chunks.append(chunk); remaining -= len(chunk)
            _need(b''.join(chunks) == expected, 'BUNDLE_REVIEW_READBACK_FAILED')
            _need(_file(os.fstat(descriptor), len(expected)) == identity
                  and _file(os.stat(name, dir_fd=directory_fd, follow_symlinks=False), len(expected)) == identity,
                  'BUNDLE_REVIEW_FILE_CHANGED')
        finally:
            if descriptor is not None:
                os.close(descriptor)
    packet.check()


def _archived_inputs(store, bundle_digest):
    _need(type(store) is BundleStore, 'BUNDLE_REVIEW_STORE_REQUIRED')
    receipt = store.inspect(bundle_digest)
    if receipt.kind == 'RAW_ARCHIVED':
        raw = store.read_raw(bundle_digest, require_backup=True)
        verified = None
        target = raw
    else:
        _need(receipt.kind == 'VERIFIED_UNAPPROVED', 'BUNDLE_REVIEW_KIND_REFUSED')
        verified = store.read_verified(bundle_digest, require_backup=True)
        raw = store.read_raw(verified.manifest.input_archive_digest, require_backup=True)
        F.validate_verified_inputs(raw.manifest, verified.manifest, limits=store.limits.format_limits)
        _need(all(verified.files[k] == value for k, value in raw.files.items()), 'BUNDLE_REVIEW_RAW_LINK_MISMATCH')
        target = verified
    _need(raw.backup_verified and target.backup_verified, 'BUNDLE_REVIEW_BACKUP_REQUIRED')
    return raw.manifest_bytes, None if verified is None else verified.manifest_bytes, dict(target.files)


def export_review_packet(store, bundle_digest, output_dir, *, requested_at, expires_at, deployment_code_hash):
    """Copy a real graph to new files; the explicit code hash remains an unsigned claim."""
    raw, verified, payloads = _archived_inputs(store, bundle_digest)
    request = A.request_from_manifests(raw, verified, requested_at=requested_at, expires_at=expires_at,
                                       deployment_code_hash=deployment_code_hash)
    A.validate_request_payloads(request, payloads)
    request_raw = A.archive_request_bytes(request)
    _need(isinstance(output_dir, Path), 'BUNDLE_REVIEW_EXPLICIT_OUTPUT_REQUIRED')
    with _PacketOutput(output_dir, store) as packet:
        written = {}
        for row in request['payload_files']:
            name = A.payload_filename(row['logical_id'])
            body = payloads[row['logical_id']]
            identity = _write_new(packet, name, body, payload=True)
            written[name] = (body, identity)
        expected_names = frozenset(written)
        _need(_names(packet.payloads, packet.payload_fd, F.DEFAULT_LIMITS.max_files+1) == expected_names
              and _names(packet.root, packet.root_fd, 3) == {'payloads'}, 'BUNDLE_REVIEW_FILE_SET_CHANGED')
        for name, (body, identity) in written.items():
            _read_back(packet, name, body, identity, payload=True)
        # Publication marker is last. Incomplete copies have no usable request;
        # readers still validate every actual file before any signature is made.
        request_identity = _write_new(packet, 'request.json', request_raw, payload=False)
        packet.sync()
        _read_back(packet, 'request.json', request_raw, request_identity, payload=False)
        for name, (body, identity) in written.items():
            _read_back(packet, name, body, identity, payload=True)
        _need(_names(packet.payloads, packet.payload_fd, F.DEFAULT_LIMITS.max_files+1) == expected_names
              and _names(packet.root, packet.root_fd, 3) == {'payloads', 'request.json'},
              'BUNDLE_REVIEW_FILE_SET_CHANGED')
        packet.check()
    return A.parse_archive_request(request_raw)


def _arguments(argv):
    _need(type(argv) in (list, tuple) and argv and all(type(v) is str for v in argv), 'BUNDLE_REVIEW_ARGUMENTS_INVALID')
    common = {'sealed-root', 'backup-root', 'head-name', 'limits', 'digest'}
    commands = {'export':common|{'out', 'requested-at', 'expires-at'}, 'authenticate':common|{'document'}}
    _need(argv[0] in commands and len(argv) == 1+2*len(commands[argv[0]]), 'BUNDLE_REVIEW_ARGUMENTS_INVALID')
    args = {}
    for key, value in zip(argv[1::2], argv[2::2]):
        _need(key.startswith('--') and key[2:] in commands[argv[0]] and key[2:] not in args
              and value and not value.startswith('--'), 'BUNDLE_REVIEW_ARGUMENTS_INVALID')
        args[key[2:]] = value
    return argv[0], args


def main(argv=None):
    try:
        command, args = _arguments(sys.argv[1:] if argv is None else argv)
        store = open_explicit_store(args['sealed-root'], args['backup-root'], args['head-name'], args['limits'])
        if command == 'export':
            current_code = owner.code_hash(owner.REPO_ROOT)
            request = export_review_packet(store, args['digest'], Path(args['out']),
                requested_at=datetime.fromisoformat(args['requested-at']), expires_at=datetime.fromisoformat(args['expires-at']),
                deployment_code_hash=current_code)
            _need(owner.code_hash(owner.REPO_ROOT) == current_code, 'BUNDLE_REVIEW_CODE_CHANGED')
            print(json.dumps({'status':'EXPORTED_UNAPPROVED', 'bundle_digest':request['bundle_digest'],
                'request_sha256':request['request_sha256'], 'scope':A.SCOPE,
                'archive_identity_authenticated':False, 'source_authenticated':False,
                'current_use_eligible':False, 'execution_ready':False}, sort_keys=True))
            return 0
        document, status = _read_snapshot(Path(args['document']), A.MAX_DOCUMENT_BYTES)
        _need(status == 'COLLECTED', 'BUNDLE_REVIEW_DOCUMENT_REFUSED')
        A.parse_attestation_document(document)
        def clock():
            return datetime.now(timezone.utc)
        assessment = authenticate_bundle_attestation(store, args['digest'], document,
            authority_provider=CurrentOwnerAuthority(clock=clock), clock=clock)
        # Assessment is display only and never fed back as an authentication token.
        output = asdict(assessment)
        output['verified_at'] = assessment.verified_at.astimezone(timezone.utc).isoformat(timespec='microseconds')
        output['status'] = 'ARCHIVE_IDENTITY_AUTHENTICATED'
        print(json.dumps(output, sort_keys=True))
        return 0
    except (ValueError, OSError, RuntimeError, TypeError, AttributeError, ArithmeticError, RecursionError) as exc:
        print(json.dumps({'status':'REFUSED', 'reasons':[_code(exc)], 'archive_identity_authenticated':False,
            'source_authenticated':False, 'current_use_eligible':False, 'execution_ready':False}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
