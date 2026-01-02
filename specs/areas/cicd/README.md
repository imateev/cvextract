# CI/CD Area

This area covers continuous integration, continuous deployment, and release automation for the cvextract project.

## Features

- [Automated Binary Releases](automated-binary-releases/README.md) - Automatic binary creation for macOS and Windows on version bumps

## Overview

The CI/CD area ensures that:
- Code quality is maintained through automated testing (see `.github/workflows/ci.yml`)
- Releases are automated and consistent
- Binaries are built and distributed automatically for end users

## Integration with Build Tools

- **bump2version**: Manages version numbers across project files
- **PyInstaller**: Creates standalone executables from Python applications
- **GitHub Actions**: Orchestrates CI/CD workflows
- **GitHub Releases**: Distributes binaries to users
