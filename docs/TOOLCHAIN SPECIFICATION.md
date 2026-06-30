# TOOLCHAIN_SPECIFICATION.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Runtime Toolchain Specification
> **Priority:** Medium

---

# 1. Purpose

This document defines the runtime toolchain used by OldButGold.

It specifies:

* bundled third-party utilities;
* bundled shared libraries;
* runtime execution rules;
* version consistency;
* update policy.

The objective is to guarantee identical behavior across supported Linux distributions.

---

# 2. Philosophy

OldButGold is a self-contained application.

The application shall never require users to install packages, libraries or runtime dependencies.

Removing the application directory shall completely remove OldButGold from the operating system.

No files shall be installed outside the application directory.

---

# 3. Runtime Architecture

The application consists of:

* the executable;
* bundled tools;
* bundled shared libraries;
* project assets;
* runtime data.

All runtime components shall remain inside the distributed directory.

---

# 4. Tool Source

Whenever technically possible, all bundled third-party utilities shall be extracted from official Alpine Linux packages.

Required shared libraries shall also originate from the same Alpine package set.

This guarantees version consistency between binaries and their dependencies.

The origin of the packages is considered part of the build process and is transparent to the end user.

---

# 5. Runtime Isolation

OldButGold shall never execute third-party utilities installed on the host operating system.

Every external utility shall be executed from:

```text
tools/
```

Shared libraries required by those utilities shall be loaded from:

```text
lib/
```

The application shall remain independent of host-installed package versions.

---

# 6. Operating System Dependencies

The operating system provides only:

* Linux kernel;
* graphical environment;
* authentication mechanism (`pkexec`);
* default terminal emulator.

Everything else required by the validation workflow belongs to OldButGold.

---

# 7. Terminal

OldButGold shall not bundle a terminal emulator.

After privilege escalation through `pkexec`, the application shall launch inside the user's default terminal environment.

The terminal itself is not part of the project.

Its only purpose is to display execution and provide a standard PTY environment.

---

# 8. Bundled Utilities

The runtime bundle shall contain every utility required by the validation pipeline.

Current required utilities are:

```text
smartctl
badblocks
lsblk
blkid
findmnt
wipefs
sgdisk
partprobe
mkfs.ext4
mkfs.ntfs
mkfs.exfat
mkfs.fat
```

Utilities shall only be added when required by an approved specification.

---

# 9. Shared Libraries

Every shared library required by bundled utilities shall also be distributed.

Libraries shall remain inside:

```text
lib/
```

The application shall configure its runtime environment so bundled utilities resolve bundled libraries before consulting host libraries whenever possible.

---

# 10. Version Consistency

All bundled utilities shall be compatible with each other.

Mixing binaries from different package revisions without validation is prohibited.

Whenever a bundled utility is updated, compatibility with the remaining bundled utilities shall be verified.

---

# 11. Tool Updates

Updating a bundled utility shall require:

* replacing the corresponding Alpine package;
* updating required shared libraries;
* validating the complete workflow;
* passing all acceptance tests.

Partial updates are discouraged.

---

# 12. Runtime Validation

During startup the application shall verify:

* bundled executable exists;
* required utilities exist;
* required shared libraries exist;
* required files are executable.

Missing runtime components shall prevent execution.

---

# 13. Integrity Verification

Whenever feasible, the application shall verify that bundled runtime files have not been corrupted.

Corrupted or incomplete bundles shall not execute.

Users shall receive a clear diagnostic message.

---

# 14. Tool Invocation

All bundled utilities shall be invoked using explicit paths.

Example:

```text
tools/smartctl
```

Using PATH resolution is prohibited.

The application shall always know exactly which executable is being launched.

---

# 15. Runtime Environment

OldButGold may configure runtime environment variables required by bundled utilities.

Examples include:

* library search paths;
* locale configuration;
* temporary directories.

These changes shall affect only the application process and its child processes.

The host operating system shall remain unchanged.

---

# 16. Build Output

The build process shall produce a runtime bundle containing only:

* required executables;
* required shared libraries;
* required assets.

Unused binaries shall not be included.

Unused libraries shall not be included.

---

# 17. Runtime Size

The runtime bundle shall remain as small as reasonably possible.

Adding new third-party utilities requires technical justification.

Redundant utilities are prohibited.

---

# 18. Tool Replacement

Replacing an existing bundled utility requires demonstrating that the replacement:

* preserves functionality;
* preserves reliability;
* preserves deterministic behavior;
* does not increase unnecessary complexity.

---

# 19. Licensing

Every bundled utility shall be legally redistributable.

Its license shall be compatible with project distribution requirements.

License notices shall accompany the distributed application whenever required.

---

# 20. Failure Policy

If any required bundled utility cannot be executed, the validation workflow shall not begin.

The application shall never silently substitute:

* host-installed binaries;
* alternative utilities;
* different implementations.

Execution shall stop with a clear explanation.

---

# 21. Engineering Rule

The runtime toolchain exists to guarantee deterministic execution.

No AI agent or contributor may:

* remove bundled utilities;
* substitute host-installed equivalents;
* introduce additional runtime dependencies;
* alter the runtime architecture;

unless explicitly authorized by an updated project specification.

The runtime bundle is considered a permanent architectural component of OldButGold.

