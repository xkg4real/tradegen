"""Actual bounded archive packets using the reviewed standalone signer reader.

These observations bind file bytes only, never research/source authenticity or
current permission. No application imports, writes, owner keys or network calls.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib

from . import contract as C
from . import authority_contract as A
from tools.signer import sign as S


def _files_body(files):
    return [A.file_document(f) for f in files]


def _packet_digest(files):
    return A.record_digest('packet',A.canonical(_files_body(files),maximum=A.MAX_DOCUMENT_BYTES))


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class PacketSnapshot:
    archive_request_bytes: bytes
    files: tuple[A.FileDigest,...]
    packet_sha256: str
    def __post_init__(self):
        request=A._archive_request(A.decode(self.archive_request_bytes,maximum=A.MAX_REQUEST_BYTES))
        C.need(S._ba_archive_request_bytes(request)==self.archive_request_bytes,'PASSKEY_TARGET_CHANGED')
        A._tuple(self.files,2049)
        for f in self.files: C.checked(f,A.FileDigest)
        C.need(tuple(f.name for f in self.files)==tuple(sorted(set(f.name for f in self.files))))
        expected=[A.FileDigest(name='request.json',byte_count=len(self.archive_request_bytes),
                              sha256=hashlib.sha256(self.archive_request_bytes).hexdigest())]
        expected.extend(A.FileDigest(name='payloads/'+S._ba_payload_filename(row['logical_id']),
            byte_count=row['byte_count'],sha256=row['sha256']) for row in request['payload_files'])
        C.need(self.files==tuple(sorted(expected,key=lambda f:f.name)),'PASSKEY_TARGET_CHANGED')
        C.hashed(self.packet_sha256); C.need(self.packet_sha256==_packet_digest(self.files),'PASSKEY_TARGET_CHANGED')


def read_packet(directory: Path) -> PacketSnapshot:
    C.need(isinstance(directory,Path),'PASSKEY_PACKET_INVALID')
    try:
        # Hold reviewed directory identities throughout both actual graph passes.
        # The signer reader streams each payload and enforces its declared hash.
        with S._BundlePin(directory) as root, S._BundlePin(directory/'payloads') as payloads:
            request,identity=S._bundle_packet(directory,pins=(root,payloads))
            raw,request_identity=S._bundle_read(directory/'request.json',S._ba_MAX_REQUEST_BYTES,parent_pin=root)
            C.need(request_identity==identity[2][0][2] and S._ba_archive_request_bytes(request)==raw,'PASSKEY_TARGET_CHANGED')
            rows=[A.FileDigest(name='request.json',byte_count=len(raw),sha256=hashlib.sha256(raw).hexdigest())]
            for name,actual,_ in identity[2][1:]:
                rows.append(A.FileDigest(name=name,byte_count=actual[0],sha256=actual[1]))
            files=tuple(sorted(rows,key=lambda f:f.name))
            result=PacketSnapshot(archive_request_bytes=raw,files=files,packet_sha256=_packet_digest(files))
            later,final_identity=S._bundle_packet(directory,pins=(root,payloads))
            C.need(final_identity==identity and S._ba_archive_request_bytes(later)==raw,'PASSKEY_TARGET_CHANGED')
            root.check(); payloads.check()
            return result
    except C.PasskeyError:
        raise
    except (OSError,ValueError,TypeError,AttributeError,OverflowError,RuntimeError):
        raise C.PasskeyError('PASSKEY_PACKET_INVALID') from None


def recheck_packet(directory: Path, expected: PacketSnapshot) -> PacketSnapshot:
    C.checked(expected,PacketSnapshot)
    result=read_packet(directory)
    C.need(result==expected,'PASSKEY_TARGET_CHANGED')
    return result


def archive_target(packet: PacketSnapshot) -> bytes:
    C.checked(packet,PacketSnapshot)
    request=A._archive_request(A.decode(packet.archive_request_bytes,maximum=A.MAX_REQUEST_BYTES))
    return A.canonical({'scope':A.SCOPE,'archive_request':request,
        'archive_request_sha256':request['request_sha256'],'packet_sha256':packet.packet_sha256,
        'approved_checks':list(S._ba_APPROVED_CHECKS)},maximum=A.MAX_REQUEST_BYTES)
