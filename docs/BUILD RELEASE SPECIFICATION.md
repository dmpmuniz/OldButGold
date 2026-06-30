# BUILD_RELEASE_SPECIFICATION.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Build & Release Specification
> **Priority:** Medium

---

# 1. Purpose

This document defines the official build and release process.

Every release shall be reproducible and deterministic.

---

# 2. Source Repository

The repository shall always remain the single source of truth.

Release artifacts shall never become development sources.

---

# 3. Build Output

Each build shall generate exactly one distributable directory.

Example:

```text
OldButGold-v1.0.0/
```

---

# 4. Bundle Assembly

The build process shall:

1. build the Python application;
2. collect bundled utilities;
3. collect required shared libraries;
4. copy project assets;
5. generate documentation;
6. validate runtime integrity.

---

# 5. Third-Party Utilities

Bundled utilities shall be extracted from official Alpine Linux packages whenever technically possible.

No manual modification of bundled executables is permitted.

---

# 6. Shared Libraries

Only libraries required by bundled executables shall be included.

Unused libraries are prohibited.

---

# 7. Validation

Before packaging, the build shall verify:

* executable exists;
* bundled tools exist;
* bundled libraries exist;
* documentation exists;
* directory structure complies with PROJECT_STRUCTURE.md.

---

# 8. Packaging

The release directory shall be compressed into a single ZIP archive.

Example:

```text
OldButGold-v1.0.0.zip
```

Nested ZIP files are prohibited.

---

# 9. Release Contents

The ZIP archive shall contain exactly one directory.

Users shall be able to extract the archive and immediately execute the application.

---

# 10. Release Verification

Before publication, the release shall pass:

* build validation;
* acceptance tests;
* runtime verification;
* documentation consistency checks.

No release shall be published if any mandatory validation fails.

---

# 11. Engineering Rule

The build process shall remain deterministic.

Running the same build from the same source revision shall produce functionally identical release artifacts.

