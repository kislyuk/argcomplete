Version 0.8.0 (2014-04-07)
--------------------------
- Refactor main body of code into a class to enable subclassing and overriding of functionality (Issue #78).

Version 0.7.1 (2014-03-29)
--------------------------
- New keyword option "argcomplete.autocomplete(validator=...)" to supply a custom validator or bypass default validation. Thanks to @thijsdezoete (Issue #77).
- Document debug options.

Version 0.7.0 (2014-01-19)
--------------------------
- New keyword option "argcomplete.autocomplete(exclude=[...])" to suppress options (Issue #74).
- More speedups to code path for global completion hook negative result.

Version 0.6.9 (2014-01-19)
--------------------------
- Fix handling of development mode script wrappers. Thanks to @jmlopez-rod and @dcosson (Issue #69).
- Speed up code path for global completion hook negative result by loading pkg_resources on demand.

Version 0.6.8 (2014-01-18)
--------------------------
- Begin tracking changes in changelog.
- Add completion support for PBR installed scripts (PR #71).
- Detect easy-install shims with shebang lines that contain Py instead of py (Issue #69).
