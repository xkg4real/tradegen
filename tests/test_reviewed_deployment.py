"""Exercise the installed checker's CLI against real local, synthetic Git commits."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from execution_launch import deployment as D


class ReviewedDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="tradegen-release-fixture-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.review = cls.root / "review"
        cls.review.mkdir()
        cls.external = cls.root / "external" / "sign.py"
        cls.external.parent.mkdir()
        cls.manifest = cls.root / "manifest.json"
        export = subprocess.run([sys.executable, "-B", "-m", "execution_launch.deployment", "export",
                                 "--repo", str(D._ROOT)], cwd=D._ROOT, check=True, capture_output=True)
        cls.manifest.write_bytes(export.stdout)
        cls.saved = json.loads(export.stdout)
        for name in [entry[0] for entry in cls.saved["repository_files"]] + ["tools/signer/sign.py"]:
            dest = cls.review / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(D._ROOT / name, dest)
        shutil.copyfile(D._ROOT / "tools/signer/sign.py", cls.external)
        cls.git("init", "-q")
        cls.git("add", "--", ".")
        cls.git("commit", "-qm", "Synthetic reviewed deployment")
        cls.commit = cls.git("rev-parse", "HEAD")
        (cls.review / "execution_launch/fixture_missing.py").write_text("pass\n", encoding="utf-8")
        cls.git("add", "--", "execution_launch/fixture_missing.py")
        cls.git("commit", "-qm", "A second reviewed deployment with one more signed source")
        cls.extended = cls.git("rev-parse", "HEAD")
        (cls.review / "execution_launch/ambiguous.PY").write_text("pass\n", encoding="ascii")
        cls.git("add", "--", "execution_launch/ambiguous.PY")
        cls.git("commit", "-qm", "Mixed-case Python extension with platform-dependent discovery")
        cls.mixed_case = cls.git("rev-parse", "HEAD")

    @classmethod
    def git(cls, *args):
        return subprocess.check_output(["git", "-C", str(cls.review), "-c", "user.name=fixture",
            "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false", *args], text=True).strip()

    def invoke(self, *, commit=None, manifest=None, signer=None, repo=None):
        cmd = [sys.executable, "-B", "-m", "tools.reviewed_deployment", "--review-repo", str(repo or self.review),
               "--commit", commit or self.commit, "--manifest", str(manifest or self.manifest),
               "--trusted-signer", str(signer or self.external)]
        result = subprocess.run(cmd, cwd=D._ROOT, capture_output=True, text=True, check=False)
        self.assertNotIn(str(self.root), result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertFalse(payload["signature_verified"])
        self.assertFalse(payload["execution_ready"])
        return result.returncode, payload

    def test_exact_commit_ignores_an_advanced_head(self):
        status, result = self.invoke()
        self.assertEqual(status, 0)
        self.assertTrue(result["comparison_passed"])
        self.assertEqual(result["reviewed_source_count"], len(self.saved["repository_files"]))
        self.assertEqual(result["reviewed_signer_sha256"], hashlib.sha256(self.external.read_bytes()).hexdigest())

    def test_extra_reviewed_seed_is_detected_even_if_the_manifest_does_not_list_it(self):
        status, result = self.invoke(commit=self.extended)
        self.assertEqual(status, 2)
        self.assertTrue(result["saved_manifest_matches_target"])
        self.assertFalse(result["target_sources_match_review"])
        self.assertEqual(self.invoke(commit=self.mixed_case)[1]["reason"], "REVIEW_SOURCE_CASE_UNSUPPORTED")

    def test_reselfhashed_manifest_subset_does_not_substitute_for_target_or_review(self):
        smaller = json.loads(self.manifest.read_bytes())
        smaller["repository_files"].pop()
        smaller["code_hash"] = D._code_hash(smaller["repository_files"], smaller["dependency_records"])
        smaller.pop("manifest_sha256")
        smaller["manifest_sha256"] = D._digest(smaller)
        path = self.root / "subset.json"
        path.write_text(json.dumps(smaller), encoding="utf-8")
        status, result = self.invoke(manifest=path)
        self.assertEqual(status, 2)
        self.assertTrue(result["target_sources_match_review"])
        self.assertFalse(result["saved_manifest_matches_target"])

    def test_a_valid_foreign_dependency_manifest_is_not_the_target_export(self):
        other = json.loads(self.manifest.read_bytes())
        other["dependency_records"][0][1] = "a" * 64
        other["code_hash"] = D._code_hash(other["repository_files"], other["dependency_records"])
        other.pop("manifest_sha256")
        other["manifest_sha256"] = D._digest(other)
        path = self.root / "other.json"
        path.write_text(json.dumps(other), encoding="utf-8")
        status, result = self.invoke(manifest=path)
        self.assertEqual(status, 2)
        self.assertFalse(result["dependency_records_match_export"])
        self.assertTrue(result["target_sources_match_review"])

    def test_signer_is_read_as_data_and_must_be_external_and_exact(self):
        altered = self.root / "altered" / "sign.py"
        altered.parent.mkdir()
        altered.write_text('raise RuntimeError("fixture must never be executed")\n', encoding="ascii")
        status, result = self.invoke(signer=altered)
        self.assertEqual(status, 2)
        self.assertTrue(result["checkout_signer_matches_review"])
        self.assertFalse(result["external_signer_matches_review"])
        self.assertEqual(self.invoke(signer=self.review / "tools/signer/sign.py")[1]["reason"],
                         "REVIEW_EXTERNAL_SIGNER_REQUIRED")

    def test_branch_abbreviations_and_noncommit_objects_are_refused(self):
        for name in ("HEAD", self.commit[:12]):
            self.assertEqual(self.invoke(commit=name)[1]["reason"], "REVIEW_FULL_COMMIT_REQUIRED")
        blob = self.git("rev-parse", "HEAD:tools/signer/sign.py")
        self.assertEqual(self.invoke(commit=blob)[1]["reason"], "REVIEW_COMMIT_REQUIRED")

    def test_40_hex_prefix_of_a_sha256_commit_is_not_a_full_commit(self):
        repo = self.root / "sha256"
        subprocess.run(["git", "init", "-q", "--object-format=sha256", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
                        "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "fixture"], check=True)
        full = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(len(full), 64)
        self.assertEqual(self.invoke(commit=full[:40], repo=repo)[1]["reason"], "REVIEW_FULL_COMMIT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
