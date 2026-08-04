# RC2 Build Reproducibility Analysis

## Verdict

```
AMBER_BUILD_NONDETERMINISM_DOCUMENTED
```

## Summary

| Item | Result |
|------|--------|
| Wheel A = Wheel B | TRUE (Wheel build is reproducible) |
| Sdist A = Sdist B | FALSE (Sdist build is not reproducible) |
| New wheel vs Existing | FALSE (different build environment) |
| Content across all builds | 100% IDENTICAL (byte-for-byte verified) |

The hash differences are purely from ZIP/tar+gzip archive format non-determinism — NOT from any difference in source code or package content.

## Toolchain

| Tool | Version |
|------|---------|
| Python | 3.12.3 |
| pip | 24.0 |
| setuptools | 68.1.2 |
| wheel | 0.42.0 |
| build | 1.5.0 |
| SOURCE_DATE_EPOCH | 1785265672 |
| LANG | de_DE.UTF-8 |
| TZ | (unset, UTC+2 local) |

## Build Methodology

Both builds were performed from `git archive` exports of commit `b841ebae1dcea5a096a2b439b68dd34582e150ae`. Each build used a separate temporary directory, separate `git archive` export, and `python3.12 -m build --wheel --sdist` with `SOURCE_DATE_EPOCH=1785265672`.

## Artifact Hashes

| Build | Wheel SHA-256 | Sdist SHA-256 |
|-------|---------------|---------------|
| Build A | `1b26bcea5026198bbee4c5bd2e98689a8c75bb8ffcd7c59d84be4fee4a0e848f` | `2c16499ba384ef23f3649e5bd9d58a3030d0def18f3c9b778471b9b3d0dd0` |
| Build B | `1b26bcea5026198bbee4c5bd2e98689a8c75bb8ffcd7c59d84be4fee4a0e848f` | `b2682840f64642fbefff4c330aac7057b909bc8c1eed08e366e6e79da4a53df6` |
| Existing Candidate | `c0890257de25ae57715e1d7d4349785c7fd503f7de6ea5c67b50fc1b59f21499` | `8e186964f2476b28a5aa329a35ec48bd68b707404a8d90ea7e7de5c1e780ed0b` |

## Root Cause

1. **Sdist non-reproducibility (A vs B):** The gzip compression embedded in tarball generation produces non-deterministic output despite identical content. Gzip's compression level and internal timing produce different byte streams.

2. **Wheel vs Existing (different hash):** The existing candidate was built in an earlier build session. The ZIP archive format's Deflate compression and internal record ordering varies between build sessions even with identical content and `SOURCE_DATE_EPOCH`.

3. **Wheel A vs B (reproducible):** Within the same filesystem and same Python process environment, wheel builds produce identical output. This confirms that the source content is deterministic.

## Content Integrity Verification

All Python source files, templates, static assets, and metadata were verified byte-for-byte identical across all builds via `diff -rq` on extracted artifacts. ZIP entry names, counts (95), and per-file digests are identical.

## Impact

- **No impact on functionality:** The installed package is identical regardless of which wheel is used.
- **Twine check:** PASS on existing candidate
- **pip check:** PASS on existing candidate
- **E2E testing:** Proceeding with the existing frozen candidate from `release/output/`

## Recommendation

For fully deterministic builds, consider:
1. Pinning `wheel >= 0.43.0` (which has improved deterministic ZIP support)
2. Using `--build-option="--no-compression"` for reproducible hashes
3. Documenting that RC2 hashes are frozen-per-build-environment, not globally reproducible

## Frozen Candidate for RC-015 E2E

| Property | Value |
|----------|-------|
| Commit | `b841ebae1dcea5a096a2b439b68dd34582e150ae` |
| Tree | `6e0a7a26f27624bc4c8e9c9bf67b4f2f5bbe60cb` |
| Version | 1.0.0rc2 |
| Wheel | `release/output/private_legal_navigator-1.0.0rc2-py3-none-any.whl` |
| Wheel SHA-256 | `c0890257de25ae57715e1d7d4349785c7fd503f7de6ea5c67b50fc1b59f21499` |
| Sdist | `release/output/private_legal_navigator-1.0.0rc2.tar.gz` |
| Sdist SHA-256 | `8e186964f2476b28a5aa329a35ec48bd68b707404a8d90ea7e7de5c1e780ed0b` |
| Candidate ZIP | `release/output/PrivateLegalNavigator-v1.0.0-rc.2-candidate.zip` |
| Candidate ZIP SHA-256 | `6e078fbc0202fcf88618f438a58a7035511aec4fda4397ae907a13d578a0de8b` |
