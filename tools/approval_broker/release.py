"""Independent installed-byte commitments; never a service-readiness issuer."""
from __future__ import annotations

import ast
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import sysconfig

from tools.signer import sign as S
from . import contract as C
from . import authority_contract as A

_MAX_FILE = 64 * 1024 * 1024
_MAX_TOTAL = 512 * 1024 * 1024
_MAX_FILES = 8192


def _read(path, maximum=_MAX_FILE):
    try:
        return S._bundle_read(path,maximum,empty=True)
    except (ValueError,OSError,TypeError):
        raise C.PasskeyError('PASSKEY_RELEASE_READ_REFUSED') from None


def _directory(path):
    C.need(isinstance(path,Path) and path.is_absolute() and '..' not in path.parts,
           'PASSKEY_RELEASE_LOCATION_INVALID')
    try:
        return S._bundle_directory(path)
    except (ValueError,OSError,TypeError):
        raise C.PasskeyError('PASSKEY_RELEASE_LOCATION_INVALID') from None


def _walk(root, *, suffixes=None):
    """Bounded exact inventory; no symlink or reparse traversal."""
    _directory(root)
    result, pending = [], [root]
    visited = 0
    while pending:
        directory = pending.pop()
        with S._BundlePin(directory) as pin:
            for name in sorted(pin.names(_MAX_FILES)):
                visited += 1
                C.need(visited <= _MAX_FILES*4,'PASSKEY_RESOURCE_LIMIT')
                item = directory/name
                info = pin.stat(name)
                if stat.S_ISDIR(info.st_mode):
                    _directory(item)
                    pending.append(item)
                else:
                    S._bundle_identity(info,regular=True)
                    if suffixes is None or any(name.endswith(suffix) for suffix in suffixes):
                        result.append(item)
                        C.need(len(result) <= _MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
    return tuple(sorted(result))


def _sites(environment):
    _directory(environment)
    candidates = []
    windows = environment/'Lib'/'site-packages'
    if windows.exists():
        candidates.append(windows)
    library = environment/'lib'
    if library.exists():
        with S._BundlePin(library) as pin:
            for name in sorted(pin.names(64)):
                if re.fullmatch(r'python[0-9]+\.[0-9]+',name):
                    candidate = library/name/'site-packages'
                    if candidate.exists():
                        candidates.append(candidate)
    C.need(len(candidates) == 1,'PASSKEY_DEPLOYMENT_REFUSED')
    _directory(candidates[0])
    return candidates[0]


def _normalized(name):
    return re.sub(r'[-_.]+','-',name).lower()


def _distributions(site):
    result, total = {}, 0
    with S._BundlePin(site) as pin:
        for name in sorted(pin.names(_MAX_FILES)):
            if not name.endswith('.dist-info'):
                continue
            directory = site/name
            _directory(directory)
            C.need(len(result)<256,'PASSKEY_RESOURCE_LIMIT')
            size = (directory/'METADATA').lstat().st_size
            C.need(0 <= size <= 2*1024*1024 and total+size <= 8*1024*1024,'PASSKEY_RESOURCE_LIMIT')
            raw, identity = _read(directory/'METADATA',2*1024*1024)
            total += len(raw)
            try:
                lines = raw.decode('utf-8').splitlines()
            except UnicodeError:
                raise C.PasskeyError('PASSKEY_DEPLOYMENT_REFUSED') from None
            names = [line[6:].strip() for line in lines if line.startswith('Name: ')]
            versions = [line[9:].strip() for line in lines if line.startswith('Version: ')]
            C.need(len(names)==len(versions)==1 and 1 <= len(names[0]) <= 128
                   and 1 <= len(versions[0]) <= 64,'PASSKEY_DEPLOYMENT_REFUSED')
            key = _normalized(names[0])
            C.need(key not in result,'PASSKEY_DEPLOYMENT_REFUSED')
            result[key] = (directory,names[0],versions[0],raw,identity)
    return result


def _target_files(repo,environment):
    """D14's exact existing source closure, with target-environment RECORDs."""
    root,root_identity = _directory(repo)
    env,env_identity = _directory(environment)
    todo = [p for base in (root/'core'/'compliance',root/'core'/'odds',root/'execution')
            for p in sorted(base.glob('*.py'))]
    for base in (root/'execution_control',root/'execution_orders',root/'execution_accounts',
                 root/'execution_network',root/'execution_launch',root/'tools'/'owner'):
        if base.exists():
            todo.extend(_walk(base,suffixes=('.py',)))
    C.need(todo,'PASSKEY_DEPLOYMENT_REFUSED')
    seen, snapshots = set(), {}
    total = 0
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        C.need(path.is_relative_to(root) and len(seen)<_MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
        size=path.lstat().st_size
        C.need(0 <= size <= _MAX_FILE and total+size <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
        raw, identity = _read(path)
        total += len(raw)
        C.need(total <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
        seen.add(path)
        snapshots[path] = (raw,identity)
        # Same reviewed AST semantics, using our bounded retained bytes only.
        tree = ast.parse(raw)
        package, names = list(path.relative_to(root).parent.parts), set()
        for node in S._import_nodes(tree,S._guards(tree)):
            if isinstance(node,ast.Import):
                names.update(alias.name for alias in node.names)
            else:
                base = package[:len(package)-node.level+1] if node.level else []
                module = '.'.join(base+([node.module] if node.module else []))
                if module:
                    names.add(module)
                    names.update(f'{module}.{alias.name}' for alias in node.names)
        todo.extend(p for name in names if (p:=S._module_file(root,name)) is not None)
        todo.extend(d/'__init__.py' for d in path.parents if d != root and d.is_relative_to(root)
                    and (d/'__init__.py').is_file())
    rows = {p.relative_to(root).as_posix():hashlib.sha256(raw).hexdigest()
            for p,(raw,_) in snapshots.items()}
    site = _sites(env)
    distributions = _distributions(site)
    for name in S._RECORD_DISTS:
        C.need(_normalized(name) in distributions,'PASSKEY_DEPLOYMENT_REFUSED')
        directory,_,version,metadata,metadata_id = distributions[_normalized(name)]
        record,identity = _read(directory/'RECORD',8*1024*1024)
        snapshots[directory/'METADATA'] = (metadata,metadata_id)
        snapshots[directory/'RECORD'] = (record,identity)
        rows[f'venv:{name}-{version}.dist-info/RECORD'] = hashlib.sha256(record).hexdigest()
    for path,expected in snapshots.items():
        C.need(_read(path,max(_MAX_FILE,len(expected[0]))) == expected,'PASSKEY_DEPLOYMENT_CHANGED')
    C.need(_directory(repo) == (root,root_identity) and _directory(environment) == (env,env_identity),
           'PASSKEY_DEPLOYMENT_CHANGED')
    return tuple(sorted(rows.items()))


def target_deployment_code_hash(repo,environment):
    """No ambient importlib.metadata: target app RECORD bytes preserve D14 wire."""
    try:
        return S.sha256_hex(S.canonical_json(_target_files(repo,environment)))
    except C.PasskeyError:
        raise
    except (ValueError,OSError,TypeError,AttributeError,RecursionError):
        raise C.PasskeyError('PASSKEY_DEPLOYMENT_REFUSED') from None


def _dependency_inventory(roots):
    expected = tuple(sorted({Path(sysconfig.get_path(name)).absolute() for name in ('purelib','platlib')}))
    C.need(type(roots) is tuple and tuple(sorted(roots)) == expected,'PASSKEY_RELEASE_LOCATION_INVALID')
    environment = Path(sys.prefix).resolve(strict=True)
    _directory(environment)
    rows, all_claimed, snapshots = [], set(), {}
    total = count = 0
    for site in roots:
        _directory(site)
        C.need(site.is_relative_to(environment),'PASSKEY_RELEASE_LOCATION_INVALID')
        for _,(directory,name,version,metadata,metadata_identity) in sorted(_distributions(site).items()):
            size=(directory/'RECORD').lstat().st_size
            C.need(0 <= size <= 8*1024*1024 and total+size <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
            record,record_identity = _read(directory/'RECORD',8*1024*1024)
            C.need(record.count(b'\n') <= _MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
            try:
                entries = csv.reader(io.StringIO(record.decode('utf-8'),newline=''))
                artifacts, claimed = [], set()
                for row in entries:
                    C.need(len(row)==3,'PASSKEY_RELEASE_INVALID')
                    C.need(count<_MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
                    relative,expected_hash,expected_size = row
                    C.need(0<len(relative)<=512 and '\\' not in relative and '\x00' not in relative
                           and not PurePosixPath(relative).is_absolute(),'PASSKEY_RELEASE_INVALID')
                    # Wheel RECORD may refer to its environment's bin/Scripts.
                    # Resolve lexical '..' only, then every actual component is pinned.
                    path = Path(os.path.abspath(site/relative))
                    C.need(path.is_relative_to(environment) and path not in claimed,'PASSKEY_RELEASE_INVALID')
                    size = path.lstat().st_size
                    C.need(0 <= size <= _MAX_FILE and total+size <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
                    raw,identity = _read(path)
                    total += len(raw); count += 1
                    C.need(total<=_MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
                    if expected_size:
                        C.need(expected_size.isascii() and expected_size.isdigit() and len(expected_size)<=19
                               and int(expected_size)==len(raw),'PASSKEY_RELEASE_CHANGED')
                    if expected_hash:
                        algorithm,encoded = expected_hash.split('=',1)
                        C.need(algorithm in ('sha256','sha384','sha512'),'PASSKEY_RELEASE_INVALID')
                        digest = hashlib.new(algorithm,raw).digest()
                        C.need(base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii') == encoded,
                               'PASSKEY_RELEASE_CHANGED')
                    else:
                        C.need(path == directory/'RECORD' or path.suffix == '.pyc','PASSKEY_RELEASE_INVALID')
                    claimed.add(path)
                    snapshots[path] = (len(raw),hashlib.sha256(raw).hexdigest(),identity)
                    artifacts.append({'name':relative,'byte_count':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
                C.need(directory/'RECORD' in claimed and directory/'METADATA' in claimed,'PASSKEY_RELEASE_INVALID')
            except C.PasskeyError:
                raise
            except (ValueError,UnicodeError,csv.Error):
                raise C.PasskeyError('PASSKEY_RELEASE_INVALID') from None
            C.need(not (claimed & all_claimed),'PASSKEY_RELEASE_INVALID')
            all_claimed.update(claimed)
            C.need(_read(directory/'RECORD',8*1024*1024)==(record,record_identity)
                   and _read(directory/'METADATA',2*1024*1024)==(metadata,metadata_identity),
                   'PASSKEY_RELEASE_CHANGED')
            rows.append(A.DependencyDigest(distribution=name,version=version,
                record_sha256=hashlib.sha256(record).hexdigest(),
                artifact_sha256=A.record_digest('dependency-artifacts',C.encoded(sorted(artifacts,key=lambda r:r['name'])))))
            C.need(len(rows)<=256,'PASSKEY_RESOURCE_LIMIT')
    actual = {path for site in roots for path in _walk(site)}
    C.need(actual == {p for p in all_claimed if any(p.is_relative_to(site) for site in roots)},
           'PASSKEY_RELEASE_INVENTORY_CHANGED')
    for path,(length,digest,identity) in snapshots.items():
        actual,actual_identity = S._bundle_read(path,_MAX_FILE,hash_only=True,empty=True)
        C.need(actual==(length,digest) and actual_identity==identity,'PASSKEY_RELEASE_CHANGED')
    return tuple(sorted(rows,key=lambda row:row.distribution))


def _stdlib_files(standard,dependency_roots):
    files,pending,visited = [],[standard],0
    while pending:
        current=pending.pop()
        with S._BundlePin(current) as pin:
            for name in sorted(pin.names(_MAX_FILES)):
                visited += 1
                C.need(visited<=_MAX_FILES*4,'PASSKEY_RESOURCE_LIMIT')
                path=current/name
                if stat.S_ISDIR(pin.stat(name).st_mode):
                    if path in dependency_roots or name in ('site-packages','dist-packages'):
                        continue
                    _directory(path); pending.append(path)
                else:
                    C.need(len(files)<_MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
                    files.append(path)
    return tuple(sorted(files))


def _shared_runtime_library():
    """Closed CPython layout, not a search-path/loader-discovery callback.

    OS loader/libc trust remains outside this release commitment. A configured
    shared CPython library is bound even if this particular launcher embeds its
    core, so the same inventory cannot silently support a different launcher.
    """
    C.need(sys.implementation.name=='cpython','PASSKEY_RUNTIME_UNSUPPORTED')
    if os.name=='nt':
        name='python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.dll'
        candidate=Path(sys.base_prefix)/name
    else:
        shared=sysconfig.get_config_var('Py_ENABLE_SHARED')
        C.need(type(shared) is int and shared in (0,1),'PASSKEY_RUNTIME_UNSUPPORTED')
        C.need(not sysconfig.get_config_var('PYTHONFRAMEWORK'),'PASSKEY_RUNTIME_UNSUPPORTED')
        if not shared:
            return None
        directory=sysconfig.get_config_var('LIBDIR');name=sysconfig.get_config_var('LDLIBRARY')
        C.need(type(directory) is str and Path(directory).is_absolute() and type(name) is str
               and re.fullmatch(r'libpython[0-9]+\.[0-9]+[a-z]*\.(?:so(?:\.[0-9]+)*|dylib)',name) is not None,
               'PASSKEY_RUNTIME_UNSUPPORTED')
        candidate=Path(directory)/name
    try:
        path=candidate.resolve(strict=True)
        _directory(path.parent)
        S._bundle_identity(path.lstat(),regular=True)
        return path
    except (OSError,ValueError):
        raise C.PasskeyError('PASSKEY_RUNTIME_UNSUPPORTED') from None


def _release_inventory(directory, *, role, dependency_roots):
    """Actual fixed virtual inventory builder, useful to explicit review tooling.

    This returns data only. It neither signs it nor provisions a service. BROKER
    commits the actual running independent package, interpreter, whole stdlib
    (including native/cache files), and every installed broker distribution.
    """
    C.need(role in ('BROKER','RP'),'PASSKEY_RELEASE_INVALID')
    root,root_identity = _directory(directory)
    package_files = _walk(root)
    rows, snapshots, total = [], {}, 0
    def add(name,path):
        nonlocal total
        size=path.lstat().st_size
        C.need(0 <= size <= _MAX_FILE and total+size <= _MAX_TOTAL and len(rows)<_MAX_FILES,
               'PASSKEY_RESOURCE_LIMIT')
        raw,identity = _read(path)
        total += len(raw)
        C.need(total <= _MAX_TOTAL and len(rows)<_MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
        snapshots[path] = (raw,identity)
        rows.append(A.FileDigest(name=name,byte_count=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    for path in package_files:
        add(('package/' if role=='BROKER' else '')+path.relative_to(root).as_posix(),path)
    if role == 'BROKER':
        installed = Path(__file__).resolve(strict=True).parents[2]
        required = set(_walk(installed/'tools'/'approval_broker'))
        required.add(installed/'tools'/'signer'/'sign.py')
        for parent in (installed/'tools',installed/'tools'/'signer'):
            if (parent/'__init__.py').exists():
                required.add(parent/'__init__.py')
        for original in required:
            target = root/original.relative_to(installed)
            C.need(target in snapshots,'PASSKEY_RELEASE_INCOMPLETE')
            C.need(_read(original)[0] == snapshots[target][0],'PASSKEY_RELEASE_CHANGED')
        executable = Path(sys.executable).resolve(strict=True)
        add('runtime/python',executable)
        shared_library = _shared_runtime_library()
        if shared_library is not None:
            add('runtime/libpython',shared_library)
        standard = Path(sysconfig.get_path('stdlib')).resolve(strict=True)
        _directory(standard)
        standard_files = _stdlib_files(standard,dependency_roots)
        for path in standard_files:
            add('runtime/stdlib/'+path.relative_to(standard).as_posix(),path)
        dependencies = _dependency_inventory(dependency_roots)
        C.need(_shared_runtime_library()==shared_library,'PASSKEY_RELEASE_CHANGED')
        C.need(_stdlib_files(standard,dependency_roots)==standard_files,'PASSKEY_RELEASE_INVENTORY_CHANGED')
    else:
        C.need(dependency_roots == (),'PASSKEY_RELEASE_LOCATION_INVALID')
        dependencies = ()
    C.need(_walk(root)==package_files and _directory(directory)==(root,root_identity),
           'PASSKEY_RELEASE_CHANGED')
    for path,expected in snapshots.items():
        C.need(_read(path)==expected,'PASSKEY_RELEASE_CHANGED')
    return A.ReleaseManifest(role=role,python_version=sys.version.split()[0],
        files=tuple(sorted(rows,key=lambda row:row.name)),dependencies=dependencies)


def verify_release(directory,manifest, *, dependency_roots):
    try:
        manifest = A.parse_release(A.release_bytes(manifest))
        actual = _release_inventory(directory,role=manifest.role,
            dependency_roots=dependency_roots if manifest.role=='BROKER' else ())
        C.need(A.release_bytes(actual)==A.release_bytes(manifest),'PASSKEY_RELEASE_CHANGED')
    except C.PasskeyError:
        raise
    except (ValueError,OSError,TypeError,AttributeError,RecursionError):
        raise C.PasskeyError('PASSKEY_RELEASE_READ_REFUSED') from None
