Version 1.2.0 (2016-05-25)
--------------------------
- Fix propagation of partially parsed subparser namespace into parent parser namespace upon subparser failure due to
  partial args. This allows completers to access partial parse results for subparser optionals in parsed_args (#114).
- The default completer can now be specified when manually instantiating CompletionFinder. Thanks to @avylove (#130).

Version 1.1.1 (2016-03-22)
--------------------------
- Use FilesCompleter as default completer fallback (#120).

Version 1.1.0 (2016-02-21)
--------------------------
- Recognize subclasses of argparse._SubParsersAction. Thanks to Stephen Koo (#118).
- Support parsed_args in custom completers with missing args. Thanks to Dan Kilman (#124).
- Non-ASCII support in FilesCompleter.
- Automatically enable FilesCompleter for argparse.FileType arguments.

Version 1.0.0 (2015-08-22)
--------------------------
- Don't print args with suppressed help by default; add
  ``argcomplete.autocomplete(print_suppressed=True)`` to control this
  behavior (#113).

Version 0.9.0 (2015-07-03)
--------------------------
- Fix always_complete_options=False support (#115).

Version 0.8.9 (2015-06-01)
--------------------------
- Correct doc filename in setup.cfg (fixes bdist_rpm failure, Issue 111).
- Make context managers exception-safe. Thanks to Mikołaj Siedlarek (pull request #110).

Version 0.8.8 (2015-05-01)
--------------------------
- Build and upload universal wheel packages in release.
- Fix issue with non-string choices for arguments. Thanks to @neizod (pull request #107).
- Improve non-ascii argparse argument support on Python 2.7.

Version 0.8.7 (2015-04-11)
--------------------------
- register-python-argcomplete: add option to avoid default readline completion. Thanks to @drmalex07 (pull request #99).

Version 0.8.6 (2015-04-11)
--------------------------
- Expand tilde in script name, allowing argcomplete to work when invoking scripts from one's home directory. Thanks to @VorpalBlade (Issue 104).

Version 0.8.5 (2015-04-07)
--------------------------
- Fix issues related to using argcomplete in a REPL environement.
- New helper method for custom completion display.
- Expand test suite; formatting cleanup.

Version 0.8.4 (2014-12-11)
--------------------------
- Fix issue related to using argcomplete in a REPL environement. Thanks to @wapiflapi (pull request #91).

Version 0.8.3 (2014-11-09)
--------------------------
- Fix multiple issues related to using argcomplete in a REPL environement. Thanks to @wapiflapi (pull request #90).

Version 0.8.2 (2014-11-03)
--------------------------
- Don't strip colon prefix in completion results if COMP_WORDBREAKS does not contain a colon. Thanks to @berezv (pull request #88).

Version 0.8.1 (2014-07-02)
--------------------------
- Use complete --nospace to avoid issues with directory completion.

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
