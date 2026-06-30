# CHANGELOG

## v0.5.2-alpha (2026-06-30)

### Feature
- Initial alpha release for community testing (Reddit)

## v0.5.1 (2026-06-30)

### Fix
- Sync version tag with GitHub release

## v0.5.0 (2026-06-28)

### Feature

* feat: remote SSH providers with server selection UI and performance fix

- Todos los providers (Docker, Swarm, K8s, Podman, OpenShift) soportan conexión SSH remota
- ServerSelectionModal con keyboard navigation (↑↓ Space Enter Escape)
- ConnectingModal con animación ▶→✓ y probing paralelo
- Dashboard funcional: selector de servidores, lista, detalles, stats, logs
- _StreamContext en SSHConnection: mata procesos zombies al cancelar
- Cache de get_env + loading en background para navegación instantánea
- Stats persistentes con bash while-loop (1 SSH en vez de 1 cada 2s) ([`ae9d189`](https://github.com/AlanStefanov/termainer/commit/ae9d18954e68ba425ef595587700bd4a46e8c5ac))

### Fix

* fix: update swarm list_containers test to match plain-text parsing ([`5da3533`](https://github.com/AlanStefanov/termainer/commit/5da3533ddc6cc380481589142a84eebfd2d317f1))

### Unknown

* Add website badge: astefanov.com ([`b0f4f85`](https://github.com/AlanStefanov/termainer/commit/b0f4f856f723751bed72f055a9d65e185c9eaffa))

## v0.4.1 (2026-06-27)

### Chore

* chore: route publication smoke-test setup through PR ([`7f70c14`](https://github.com/AlanStefanov/termainer/commit/7f70c14f2d3ec58db0546e4005bc52d37a3774de))

### Ci

* ci: split semantic-release into version and publish steps ([`e68744c`](https://github.com/AlanStefanov/termainer/commit/e68744c4f4e33b7283b704f9054362c9179b7564))

* ci: remove publish/release workflows, use local publish.sh instead ([`a0dc899`](https://github.com/AlanStefanov/termainer/commit/a0dc899c5afb7af999db2192a689ffc8b9249024))

* ci: mark homebrew tap job as continue-on-error until tap is configured ([`e93d82b`](https://github.com/AlanStefanov/termainer/commit/e93d82be4c7fa4a405bb91b84e52e65adceea40b))

* ci: fix checkout ref for workflow_dispatch manual triggers ([`0391a6f`](https://github.com/AlanStefanov/termainer/commit/0391a6f3ad27146a04dab981fe668e310fbe7d89))

* ci: add workflow_dispatch to publish.yml for manual triggers ([`80f6898`](https://github.com/AlanStefanov/termainer/commit/80f68987c436509eaa5ebd9a9b8918a9552cf608))

### Fix

* fix: add fetch-tags and verbose to release job ([`7c34e92`](https://github.com/AlanStefanov/termainer/commit/7c34e920073a162b80c07433266622ec7837c0b8))

* fix: pin python-semantic-release to v9 in CI

v10 changed CLI and config format; config is written for v9 ([`3bc5035`](https://github.com/AlanStefanov/termainer/commit/3bc50354dba24b7dae586b0fc7fa181dbe046b78))

* fix: include non-Python assets in wheel

- Use importlib.resources.files for CSS_PATH resolution
- Add MANIFEST.in with recursive-include for ui/* assets
- Enable include-package-data in pyproject.toml
- Add release job to CI that runs semantic-release on push to main
- Enable upload_to_release for automatic GitHub Releases with changelog ([`547a56d`](https://github.com/AlanStefanov/termainer/commit/547a56d03035b11e71e657db00baf0c7759f2b71))

* fix: include non-Python assets in wheel

- Add package_data to pyproject.toml for ui/* assets
- Use importlib.resources.files for CSS_PATH resolution
  so Textual can find styles.tcss at runtime ([`e12c1ec`](https://github.com/AlanStefanov/termainer/commit/e12c1ec609d8f7722b32ace569e9fda4e82391a1))

### Test

* test: trust homebrew tap in brew smoke test ([`70ce5dc`](https://github.com/AlanStefanov/termainer/commit/70ce5dc5787da41b2fd84f457d09c4d20dd59019))

* test: add doctor command and installation smoke tests ([`16dd06a`](https://github.com/AlanStefanov/termainer/commit/16dd06abc3cb445f578fd242281ea1cf5c587149))

### Unknown

* Merge pull request #6 from AlanStefanov/hotfix/assets-in-wheel

fix: include non-Python assets in wheel + CI release automation ([`2bd13e9`](https://github.com/AlanStefanov/termainer/commit/2bd13e9ad9cf529bc9d7581316d6369a57ab87c7))

* Revert &#34;Merge pull request #5 from AlanStefanov/hotfix/assets-in-wheel&#34;

This reverts commit 3482ec1b06ec23ad6c752ac405180dff72dca0c5, reversing
changes made to 70ce5dc5787da41b2fd84f457d09c4d20dd59019. ([`6385b69`](https://github.com/AlanStefanov/termainer/commit/6385b693aa35c173af2d872ef6fc9574c21449f3))

* Merge pull request #5 from AlanStefanov/hotfix/assets-in-wheel

fix: include non-Python assets in wheel ([`3482ec1`](https://github.com/AlanStefanov/termainer/commit/3482ec1b06ec23ad6c752ac405180dff72dca0c5))

* Merge pull request #4 from AlanStefanov/feature/publication-smoke-tests

chore: publication smoke-test workflow ([`1eb6422`](https://github.com/AlanStefanov/termainer/commit/1eb6422da55bc68dbc097ae0751fe17621105bed))

## v0.4.0 (2026-06-27)

### Feature

* feat(ui): v0.4.0 — Boot animation, widget-based Home &amp; Environment selector (#3)

* feat(ui): redesign Home with boot animation and widget architecture

- Replace SplashScreen with animated BootScreen (6-step boot sequence,
  auto-transitions to HomeScreen in ~1s, Enter/Space to skip)
- Refactor HomeScreen into independent composable widgets:
  HeaderWidget, HeroWidget, PlatformsStripWidget, AboutWidget,
  FeaturesWidget, SupportedPlatformsWidget, FooterWidget
- New visual identity: #66FF33 green, #00E5FF cyan, per-platform colors
- Remove &#39;Inicio Rapido&#39; section; footer shows only Enter hint + credits
- Add EnvironmentScreen selector with back navigation (b/Esc) from Dashboard
- Dashboard: add &#39;back to environment&#39; binding (b/Esc), footer key
- Fix on_key propagation from BootScreen/HomeScreen so Enter doesn&#39;t
  cascade into child screens
- Bump version to 0.4.0

* ci: split workflows into ci / release / publish + add Homebrew tap support

- ci.yml: pure CI (lint + test), fires on all branches, never on tags
- release.yml: semantic-release on merge to main; creates tag + CHANGELOG
- publish.yml: triggered by new tag v* from semantic-release
    - PyPI: build + twine upload
    - Docker: multi-arch (amd64/arm64) push to Docker Hub + GHCR
    - Homebrew: waits for PyPI, computes SHA256, patches Formula in
      homebrew-termainer tap repo and pushes commit
- .github/homebrew/termainer.rb: formula template for tap repo
- Delete conflicting v0.4.0 tag (re-created by semantic-release after merge)

* ci(publish): switch PyPI to OIDC trusted publisher (no token needed) ([`9156fc4`](https://github.com/AlanStefanov/termainer/commit/9156fc47bf118e8c1fa66f7ccfbe25b4fbfc60d9))

### Fix

* fix(ci): run semantic-release version before publish to actually create tag ([`3a903f7`](https://github.com/AlanStefanov/termainer/commit/3a903f75eb298708e8f07a7c4f00988aebbf45c6))

* fix(ci): use GH_PAT for semantic-release to allow triggering downstream workflows ([`4126f2b`](https://github.com/AlanStefanov/termainer/commit/4126f2b982276bbfde2835cfcaeed446bcc95891))

* fix(ci): pin semantic-release to v9, fix config (build_command, remove unsupported keys) ([`527f37d`](https://github.com/AlanStefanov/termainer/commit/527f37deea1fa0f299e92205a431df6154019d9c))

* fix(ci): remove unused Center import and fix version_toml format for semantic-release v9 ([`76c2373`](https://github.com/AlanStefanov/termainer/commit/76c23730ccdd4f4f961d7b5d676eb7d29d481eb0))

## v0.3.0 (2026-06-27)

## v0.2.1 (2026-06-25)

### Feature

* feat: responsive UI polish and repo hardening ([`308f5af`](https://github.com/AlanStefanov/termainer/commit/308f5af160108ca14d978872e6d9158b4e2d44d2))

* feat(ui): dynamic splash density, 10s intro, and enter hint ([`fb70a49`](https://github.com/AlanStefanov/termainer/commit/fb70a495ce02dfe1cb084302611da22bc0b10556))

* feat(ui): add responsive modes for dashboard, home, and environment ([`ed283d8`](https://github.com/AlanStefanov/termainer/commit/ed283d8e152c24f35e0910542498f194d9d3d22d))

* feat: refresh docs, enable swarm, and refine TUI flow ([`11f645b`](https://github.com/AlanStefanov/termainer/commit/11f645b03cd755116a66d5d7fd19cc63c5110829))

### Fix

* fix(ui): preserve splash content in responsive modes ([`161986f`](https://github.com/AlanStefanov/termainer/commit/161986fd86de4a1367989b3a58c5ff3015e22e80))

### Unknown

* Merge pull request #1 from AlanStefanov/feature/tui-resposive

feat: responsive UI polish and repo hardening ([`ac12496`](https://github.com/AlanStefanov/termainer/commit/ac124969c059190e2edda8ac25d72891d636041a))
