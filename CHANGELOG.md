# CHANGELOG


## v0.4.0 (2026-06-27)

### Bug Fixes

- **ci**: Pin semantic-release to v9, fix config (build_command, remove unsupported keys)
  ([`527f37d`](https://github.com/AlanStefanov/termainer/commit/527f37deea1fa0f299e92205a431df6154019d9c))

- **ci**: Remove unused Center import and fix version_toml format for semantic-release v9
  ([`76c2373`](https://github.com/AlanStefanov/termainer/commit/76c23730ccdd4f4f961d7b5d676eb7d29d481eb0))

- **ci**: Run semantic-release version before publish to actually create tag
  ([`3a903f7`](https://github.com/AlanStefanov/termainer/commit/3a903f75eb298708e8f07a7c4f00988aebbf45c6))

- **ci**: Use GH_PAT for semantic-release to allow triggering downstream workflows
  ([`4126f2b`](https://github.com/AlanStefanov/termainer/commit/4126f2b982276bbfde2835cfcaeed446bcc95891))

### Features

- **ui**: V0.4.0 — Boot animation, widget-based Home & Environment selector
  ([#3](https://github.com/AlanStefanov/termainer/pull/3),
  [`9156fc4`](https://github.com/AlanStefanov/termainer/commit/9156fc47bf118e8c1fa66f7ccfbe25b4fbfc60d9))

* feat(ui): redesign Home with boot animation and widget architecture

- Replace SplashScreen with animated BootScreen (6-step boot sequence, auto-transitions to
  HomeScreen in ~1s, Enter/Space to skip) - Refactor HomeScreen into independent composable widgets:
  HeaderWidget, HeroWidget, PlatformsStripWidget, AboutWidget, FeaturesWidget,
  SupportedPlatformsWidget, FooterWidget - New visual identity: #66FF33 green, #00E5FF cyan,
  per-platform colors - Remove 'Inicio Rapido' section; footer shows only Enter hint + credits - Add
  EnvironmentScreen selector with back navigation (b/Esc) from Dashboard - Dashboard: add 'back to
  environment' binding (b/Esc), footer key - Fix on_key propagation from BootScreen/HomeScreen so
  Enter doesn't cascade into child screens - Bump version to 0.4.0

* ci: split workflows into ci / release / publish + add Homebrew tap support

- ci.yml: pure CI (lint + test), fires on all branches, never on tags - release.yml:
  semantic-release on merge to main; creates tag + CHANGELOG - publish.yml: triggered by new tag v*
  from semantic-release - PyPI: build + twine upload - Docker: multi-arch (amd64/arm64) push to
  Docker Hub + GHCR - Homebrew: waits for PyPI, computes SHA256, patches Formula in
  homebrew-termainer tap repo and pushes commit - .github/homebrew/termainer.rb: formula template
  for tap repo - Delete conflicting v0.4.0 tag (re-created by semantic-release after merge)

* ci(publish): switch PyPI to OIDC trusted publisher (no token needed)


## v0.3.0 (2026-06-27)


## v0.2.1 (2026-06-25)

### Bug Fixes

- **ui**: Preserve splash content in responsive modes
  ([`161986f`](https://github.com/AlanStefanov/termainer/commit/161986fd86de4a1367989b3a58c5ff3015e22e80))

### Features

- Refresh docs, enable swarm, and refine TUI flow
  ([`11f645b`](https://github.com/AlanStefanov/termainer/commit/11f645b03cd755116a66d5d7fd19cc63c5110829))

- Responsive UI polish and repo hardening
  ([`308f5af`](https://github.com/AlanStefanov/termainer/commit/308f5af160108ca14d978872e6d9158b4e2d44d2))

- **ui**: Add responsive modes for dashboard, home, and environment
  ([`ed283d8`](https://github.com/AlanStefanov/termainer/commit/ed283d8e152c24f35e0910542498f194d9d3d22d))

- **ui**: Dynamic splash density, 10s intro, and enter hint
  ([`fb70a49`](https://github.com/AlanStefanov/termainer/commit/fb70a495ce02dfe1cb084302611da22bc0b10556))
