Version 0.6.9 (2014-01-19)
--------------------------
- Fix handling of development mode script wrappers. Thanks to @jmlopez-rod and @dcosson (Issue #69).
- Speed up code path for global completion hook negative result by loading pkg_resources on demand.

Version 0.6.8 (2014-01-18)
--------------------------
- Begin tracking changes in changelog.
- Add completion support for PBR installed scripts (PR #71).
- Detect easy-install shims with shebang lines that contain Py instead of py (Issue #69).
