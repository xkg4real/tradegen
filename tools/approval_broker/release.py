"""Independent installed-byte commitments; never a service-readiness issuer."""
from __future__ import annotations

import ast
import base64
import contextlib
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


def _read(path, maximum=_MAX_FILE, *, pin=None, info=None):
    try:
        return S._bundle_read(path,maximum,empty=True,parent_pin=pin,initial=info)
    except (ValueError,OSError,TypeError,RuntimeError):
        raise C.PasskeyError('PASSKEY_RELEASE_READ_REFUSED') from None


def _directory(path):
    C.need(isinstance(path,Path) and path.is_absolute() and '..' not in path.parts,
           'PASSKEY_RELEASE_LOCATION_INVALID')
    try:
        return S._bundle_directory(path)
    except (ValueError,OSError,TypeError,RuntimeError):
        raise C.PasskeyError('PASSKEY_RELEASE_LOCATION_INVALID') from None


def _pinned(stack, directory, parent=None, code='PASSKEY_RELEASE_LOCATION_INVALID'):
    """A directory pin held by `stack`; from a held `parent` only the new component is reviewed."""
    try:
        return stack.enter_context(S._BundlePin(directory,parent=parent))
    except (ValueError,OSError,TypeError,RuntimeError):
        raise C.PasskeyError(code) from None


def _pins(stack, base):
    """Pins held for one pass: one per directory, one under `base` entered from its held parent, so each
    ancestry is reviewed once rather than per file. Never kept beyond the pass (`stack`). Keyed by the exact
    spelling: Windows Path equality is str.lower(), which joins distinct NTFS folders ('broker' and 'bro'
    U+212A 'er', or two folders of a case-sensitive directory), and a shared pin would read the wrong one."""
    held = {}
    def pin(directory):
        key = str(directory)
        if key not in held:
            parent = pin(directory.parent) if key != str(base) and directory.is_relative_to(base) else None
            held[key] = _pinned(stack,directory,parent,'PASSKEY_RELEASE_READ_REFUSED')
        return held[key]
    return pin


def _walk(root, *, suffixes=None, skip=None, read=None):
    """Bounded exact inventory; no symlink or reparse traversal. Each directory is pinned once, from its held
    parent, and `read(pin,path,info)` sees every listed file under that same pin."""
    _directory(root)
    result, visited = [], 0
    def visit(directory, parent):
        nonlocal visited
        with contextlib.ExitStack() as stack:
            pin = _pinned(stack,directory,parent)
            names = sorted(pin.names(_MAX_FILES))
            # Windows Path equality is str.lower(): distinct NTFS names it joins ('kdf' and U+212A 'df', or two
            # names in a case-sensitive folder) would share one Path-keyed entry; refuse them. The file-keyed
            # containers and listing compares of this module use the exact str spelling as well.
            # Win32 also strips a trailing '.' or ' ' (a \\?\-created 'm.py.' would be read as 'm.py'); refuse it.
            C.need(len({directory/name for name in names}) == len(names)
                   and not (os.name == 'nt' and any(name.endswith(('.',' ')) for name in names)),
                   'PASSKEY_RELEASE_READ_REFUSED')
            for name in names:
                visited += 1
                C.need(visited <= _MAX_FILES*4,'PASSKEY_RESOURCE_LIMIT')
                item = directory/name
                info = pin.stat(name)
                if stat.S_ISDIR(info.st_mode):
                    if skip is None or not skip(item):
                        visit(item,pin)
                else:
                    S._bundle_identity(info,regular=True)
                    if suffixes is None or any(name.endswith(suffix) for suffix in suffixes):
                        result.append(item)
                        C.need(len(result) <= _MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
                        if read is not None:
                            read(pin,item,info)
    visit(root,None)
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


def _distributions(site, *, required=None):
    result, total = {}, 0
    # A target D14 scan needs precisely the original two distributions. The
    # broker release deliberately leaves this unset and verifies every one.
    if required is not None:
        C.need(type(required) is tuple and required == S._RECORD_DISTS,'PASSKEY_DEPLOYMENT_REFUSED')
        required = frozenset(_normalized(name) for name in required)
    with S._BundlePin(site) as pin:
        for name in sorted(pin.names(_MAX_FILES)):
            if not name.endswith('.dist-info'):
                continue
            directory_name, separator, directory_version = name[:-10].rpartition('-')
            if required is not None:
                candidate = _normalized(directory_name if separator else name[:-10])
                if candidate not in required:
                    continue
                C.need(separator and directory_name and directory_version,'PASSKEY_DEPLOYMENT_REFUSED')
            directory = site/name
            C.need(len(result)<256,'PASSKEY_RESOURCE_LIMIT')
            with contextlib.ExitStack() as stack:
                held = _pinned(stack,directory,pin)
                size = held.stat('METADATA').st_size
                C.need(0 <= size <= 2*1024*1024 and total+size <= 8*1024*1024,'PASSKEY_RESOURCE_LIMIT')
                raw, identity = _read(directory/'METADATA',2*1024*1024,pin=held)
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
            if required is not None:
                C.need(key == candidate and versions[0] == directory_version,'PASSKEY_DEPLOYMENT_REFUSED')
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
    with contextlib.ExitStack() as stack:
        pin = _pins(stack,root)  # every directory of the closure pinned once, from its held parent
        seen, snapshots = {}, {}  # seen: first spelling per Path (case-fold); snapshots: every exact spelling
        total = 0
        while todo:
            path = todo.pop()
            if str(path) in snapshots:
                continue
            C.need(path.is_relative_to(root) and len(snapshots)<_MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
            size=path.lstat().st_size
            C.need(0 <= size <= _MAX_FILE and total+size <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
            raw, identity = _read(path,pin=pin(path.parent))
            total += len(raw)
            C.need(total <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
            snapshots[str(path)] = (raw,identity)
            # A case-fold spelling of a read file (an import probe such as core/odds/O.py for core/odds/o.py) is
            # skipped as before and in sign.code_files once its read shows the same file; a distinct file refuses.
            if path in seen:
                C.need(seen[path] == identity,'PASSKEY_DEPLOYMENT_REFUSED')
                continue
            seen[path] = identity
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
        rows = {p.relative_to(root).as_posix():hashlib.sha256(snapshots[str(p)][0]).hexdigest() for p in seen}
        site = _sites(env)
        distributions = _distributions(site,required=S._RECORD_DISTS)
        for name in S._RECORD_DISTS:
            C.need(_normalized(name) in distributions,'PASSKEY_DEPLOYMENT_REFUSED')
            directory,_,version,metadata,metadata_id = distributions[_normalized(name)]
            record,identity = _read(directory/'RECORD',8*1024*1024,pin=pin(directory))
            snapshots[str(directory/'METADATA')] = (metadata,metadata_id)
            snapshots[str(directory/'RECORD')] = (record,identity)
            rows[f'venv:{name}-{version}.dist-info/RECORD'] = hashlib.sha256(record).hexdigest()
        for key,expected in snapshots.items():
            path = Path(key)
            C.need(_read(path,max(_MAX_FILE,len(expected[0])),pin=pin(path.parent)) == expected,
                   'PASSKEY_DEPLOYMENT_CHANGED')
    C.need(_directory(repo) == (root,root_identity) and _directory(environment) == (env,env_identity),
           'PASSKEY_DEPLOYMENT_CHANGED')
    return tuple(sorted(rows.items()))


def target_deployment_code_hash(repo,environment):
    """No ambient importlib.metadata: target app RECORD bytes preserve D14 wire."""
    try:
        return S.sha256_hex(S.canonical_json(_target_files(repo,environment)))
    except C.PasskeyError:
        raise
    except (ValueError,OSError,TypeError,AttributeError,RecursionError,RuntimeError):
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
        distributions = sorted(_distributions(site).items())
        # One pinned walk reads every installed file once (each directory's ancestry reviewed once, not per
        # file); RECORD rows are checked against these reads and the final walk below reads them all again.
        installed = {}  # exact str keys, as `snapshots` and `again` below
        def first(pin,path,info):
            nonlocal total
            C.need(0 <= info.st_size <= _MAX_FILE and total+info.st_size <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
            installed[str(path)] = _read(path,pin=pin,info=info)
            total += len(installed[str(path)][0])
            C.need(total<=_MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
        _walk(site,read=first)
        for _,(directory,name,version,metadata,metadata_identity) in distributions:
            with contextlib.ExitStack() as stack:
                pin = _pins(stack,environment)
                size=pin(directory).stat('RECORD').st_size
                C.need(0 <= size <= 8*1024*1024 and total+size <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
                record,record_identity = _read(directory/'RECORD',8*1024*1024,pin=pin(directory))
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
                        if str(path) in installed:
                            raw,identity = installed.pop(str(path))
                        else:
                            size = path.lstat().st_size
                            C.need(0 <= size <= _MAX_FILE and total+size <= _MAX_TOTAL,'PASSKEY_RESOURCE_LIMIT')
                            raw,identity = _read(path,pin=pin(path.parent))
                            total += len(raw)
                        count += 1
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
                            C.need(str(path) == str(directory/'RECORD') or path.suffix == '.pyc','PASSKEY_RELEASE_INVALID')
                        claimed.add(path)  # Path set kept: its case-fold only refuses more (twin rows, overlaps)
                        digest = hashlib.sha256(raw).hexdigest()
                        snapshots[str(path)] = (len(raw),digest,identity)
                        artifacts.append({'name':relative,'byte_count':len(raw),'sha256':digest})
                    C.need(directory/'RECORD' in claimed and directory/'METADATA' in claimed,'PASSKEY_RELEASE_INVALID')
                except C.PasskeyError:
                    raise
                except (ValueError,UnicodeError,csv.Error):
                    raise C.PasskeyError('PASSKEY_RELEASE_INVALID') from None
                C.need(not (claimed & all_claimed),'PASSKEY_RELEASE_INVALID')
                all_claimed.update(claimed)
                C.need(_read(directory/'RECORD',8*1024*1024,pin=pin(directory))==(record,record_identity)
                       and _read(directory/'METADATA',2*1024*1024,pin=pin(directory))==(metadata,metadata_identity),
                       'PASSKEY_RELEASE_CHANGED')
                rows.append(A.DependencyDigest(distribution=name,version=version,
                    record_sha256=hashlib.sha256(record).hexdigest(),
                    artifact_sha256=A.record_digest('dependency-artifacts',C.encoded(sorted(artifacts,key=lambda r:r['name'])))))
                C.need(len(rows)<=256,'PASSKEY_RESOURCE_LIMIT')
    # Second pass: one pinned walk lists every installed file and re-reads it under that same pin.
    again = {}
    def last(pin,path,info):
        again[str(path)] = S._bundle_read(path,_MAX_FILE,hash_only=True,empty=True,parent_pin=pin,initial=info)
    actual = {str(path) for site in roots for path in _walk(site,read=last)}
    C.need(actual == {str(p) for p in all_claimed if any(p.is_relative_to(site) for site in roots)},
           'PASSKEY_RELEASE_INVENTORY_CHANGED')
    for path,(length,digest,identity) in snapshots.items():
        actual,actual_identity = (again[path] if path in again
                                  else S._bundle_read(path,_MAX_FILE,hash_only=True,empty=True))
        C.need(actual==(length,digest) and actual_identity==identity,'PASSKEY_RELEASE_CHANGED')
    return tuple(sorted(rows,key=lambda row:row.distribution))


def _stdlib_files(standard,dependency_roots,read=None):
    return _walk(standard,read=read,skip=lambda path:path in dependency_roots
                 or path.name in ('site-packages','dist-packages'))


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
    rows, snapshots, total, rechecked = [], {}, 0, set()
    def add(name,path,pin=None,info=None):
        nonlocal total
        size=(path.lstat() if info is None else info).st_size
        C.need(0 <= size <= _MAX_FILE and total+size <= _MAX_TOTAL and len(rows)<_MAX_FILES,
               'PASSKEY_RESOURCE_LIMIT')
        raw,identity = _read(path,pin=pin,info=info)
        total += len(raw)
        C.need(total <= _MAX_TOTAL and len(rows)<_MAX_FILES,'PASSKEY_RESOURCE_LIMIT')
        snapshots[str(path)] = (raw,identity)  # exact str keys, `rechecked` too: a case-fold rename is no match
        rows.append(A.FileDigest(name=name,byte_count=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    def again(pin,path,info):
        # Final pass under the listing walk's own pins; an added, removed or renamed file fails that listing's
        # exact compare.
        if str(path) in snapshots:
            C.need(_read(path,pin=pin,info=info)==snapshots[str(path)],'PASSKEY_RELEASE_CHANGED')
            rechecked.add(str(path))
    package_files = _walk(root,read=lambda pin,path,info:add(
        ('package/' if role=='BROKER' else '')+path.relative_to(root).as_posix(),path,pin,info))
    if role == 'BROKER':
        installed = Path(__file__).resolve(strict=True).parents[2]
        required = set(_walk(installed/'tools'/'approval_broker'))
        required.add(installed/'tools'/'signer'/'sign.py')
        for parent in (installed/'tools',installed/'tools'/'signer'):
            if (parent/'__init__.py').exists():
                required.add(parent/'__init__.py')
        with contextlib.ExitStack() as stack:
            pin = _pins(stack,installed)
            for original in required:
                target = str(root/original.relative_to(installed))
                C.need(target in snapshots,'PASSKEY_RELEASE_INCOMPLETE')
                C.need(_read(original,pin=pin(original.parent))[0] == snapshots[target][0],'PASSKEY_RELEASE_CHANGED')
        executable = Path(sys.executable).resolve(strict=True)
        add('runtime/python',executable)
        shared_library = _shared_runtime_library()
        if shared_library is not None:
            add('runtime/libpython',shared_library)
        standard = Path(sysconfig.get_path('stdlib')).resolve(strict=True)
        _directory(standard)
        standard_files = _stdlib_files(standard,dependency_roots,read=lambda pin,path,info:add(
            'runtime/stdlib/'+path.relative_to(standard).as_posix(),path,pin,info))
        dependencies = _dependency_inventory(dependency_roots)
        C.need(str(_shared_runtime_library())==str(shared_library),'PASSKEY_RELEASE_CHANGED')
        C.need(tuple(map(str,_stdlib_files(standard,dependency_roots,read=again)))==tuple(map(str,standard_files)),
               'PASSKEY_RELEASE_INVENTORY_CHANGED')
    else:
        C.need(dependency_roots == (),'PASSKEY_RELEASE_LOCATION_INVALID')
        dependencies = ()
    C.need(tuple(map(str,_walk(root,read=again)))==tuple(map(str,package_files))
           and _directory(directory)==(root,root_identity),'PASSKEY_RELEASE_CHANGED')
    for path,expected in snapshots.items():
        if path not in rechecked:
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
    except (ValueError,OSError,TypeError,AttributeError,RecursionError,RuntimeError):
        raise C.PasskeyError('PASSKEY_RELEASE_READ_REFUSED') from None
