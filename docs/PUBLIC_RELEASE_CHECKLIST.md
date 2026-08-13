# Public release checklist

Status date: 2026-08-14. `[x]` is verified in this workspace; `[ ]` remains a maintainer action before public release.

- [x] Project name, UI, screenshots, examples, and README are platform-neutral.
- [x] Repository screenshots and tests use only the self-created synthetic demo media.
- [x] Upstream MIT copyright notice and `NOTICE.md` attribution are preserved.
- [x] README states authorized-use boundaries and user responsibility for law, contracts, licenses, platform terms, disclosure, and attribution.
- [x] README states project independence and that it provides no legal advice.
- [x] Marketing language does not claim payment/access/platform restriction circumvention.
- [x] Application runs locally without media upload or telemetry.
- [x] Fixed FFmpeg 9.0.1 x64 build source, version, license, configuration and SHA-256 are recorded; license/readme ship in each release directory.
- [x] Windows x64 PyInstaller and Nuitka standalone release directories were built and launched on the development host without invoking Python.
- [x] macOS PyInstaller source, pinned per-architecture FFmpeg preparation, Apple Silicon/Intel CI matrix, Finder integration, and packaged self-test are implemented.
- [x] Apple Silicon `.app` was built, ad-hoc signed, deeply verified, and exercised through its packaged end-to-end self-test; Intel is covered by the CI build matrix.
- [x] Automated tests, synthetic E2E export, media verification, and GUI screenshot suite pass; see `docs/VERIFICATION_REPORT.md`.
- [x] SHA-256 generation script is included and release hashes are published in `release/SHA256SUMS.txt`.
- [ ] Test both packaged releases in a genuinely clean Windows 10/11 x64 VM and archive evidence. Sandbox/Hyper-V was unavailable without elevation in this session.
- [ ] Run antivirus scans on final ZIP assets and record engine, definitions date, and results.
- [ ] Decide whether to Authenticode-sign the EXE files and document the publisher identity.
- [ ] Sign macOS archives with Developer ID, notarize them with Apple, staple the ticket, and verify Gatekeeper acceptance on clean Apple Silicon and Intel Macs.
- [ ] Confirm and publish the GPLv3 corresponding-source/source-offer mechanism for the exact bundled FFmpeg build.
- [ ] Immediately before making the repository public, manually review full Git history and release assets for private media, third-party marks, tokens, local usernames/paths, and other sensitive material.
- [ ] Obtain a final human legal/licensing review if the maintainer requires one; this checklist is engineering guidance, not legal advice.
