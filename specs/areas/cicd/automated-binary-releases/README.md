# Automated Binary Releases

**Status**: Active  
**Entry Point**: `.github/workflows/release.yml`  
**Config/Env**: Version bumps via `bump2version`, PyInstaller spec at `cvextract.spec`

## Feature Description

Automatically builds standalone binaries for macOS and Windows whenever a new version is released, and attaches them to the corresponding GitHub Release.

## Motivation

- **Simplifies distribution**: Users can download and run the app without installing Python or dependencies
- **Ensures consistency**: Every release is immediately usable on both major platforms
- **Improves adoption**: Reduces setup friction for non-technical users

## How It Works

### Trigger Mechanism

The workflow is triggered when a commit message matches the pattern `Bump version: x.y.z → a.b.c`, which is the format used by `bump2version`.

### Workflow Steps

1. **Detect Version Bump**: Parse commit message to extract new version number
2. **Create Release**: Create a GitHub Release with the version tag
3. **Build Binaries**: 
   - Build macOS binary using PyInstaller on `macos-latest` runner
   - Build Windows binary using PyInstaller on `windows-latest` runner
4. **Upload Assets**: Attach binaries to the GitHub Release

### Binary Naming Convention

- macOS: `cvextract-{version}-macos`
- Windows: `cvextract-{version}-windows.exe`

## Configuration

### PyInstaller Spec File

The `cvextract.spec` file at the root of the repository configures PyInstaller to:
- Bundle all dependencies into a single executable
- Use the CLI entry point (`cvextract/cli.py`)
- Create console applications (not windowed)
- Use UPX compression where available

### Bumpversion Configuration

The `.bumpversion.cfg` file is configured to:
- Update version in `pyproject.toml`
- Create commits automatically
- Create tags automatically (tag = True)

## Usage

### For Maintainers

To release a new version:

```bash
# Bump patch version (0.5.1 → 0.5.2)
bump2version patch

# Bump minor version (0.5.1 → 0.6.0)
bump2version minor

# Bump major version (0.5.1 → 1.0.0)
bump2version major

# Push the commit and tags
git push origin main --tags
```

The GitHub Actions workflow will automatically:
1. Detect the version bump commit
2. Create a GitHub Release
3. Build binaries for macOS and Windows
4. Upload binaries to the Release

### For Users

Users can download pre-built binaries from the [Releases](https://github.com/imateev/cvextract/releases) page:

1. Go to the Releases section
2. Download the binary for your platform
3. Run the binary directly (no Python installation required)

## Implementation Details

### Workflow File Location

`.github/workflows/release.yml`

### Key Workflow Features

- **Trigger**: Runs on push to main branch with version bump commit message
- **Parallel Builds**: macOS and Windows binaries are built in parallel
- **Dependency Management**: PyInstaller and dependencies are installed automatically
- **Asset Upload**: Uses GitHub Actions to upload binaries to the release

### Dependencies

The workflow requires:
- PyInstaller (installed in workflow)
- Project dependencies (lxml, docxtpl, requests, openai)
- Platform-specific runners (macos-latest, windows-latest)

## Testing

### Local Testing

To test PyInstaller builds locally:

```bash
# Install PyInstaller
pip install pyinstaller

# Build using the spec file
pyinstaller cvextract.spec

# Test the binary
./dist/cvextract --help
```

### CI Testing

The workflow can be tested by creating a feature branch with a test version bump commit.

## Limitations

- Only builds for macOS and Windows (Linux users can use Python package)
- Requires version bump via `bump2version` for automation
- Binary size may be large due to bundled dependencies
- First-time builds may take several minutes

## Future Enhancements

- Add Linux binary support
- Implement binary signing for macOS and Windows
- Add automated testing of built binaries
- Cache dependencies to speed up builds
- Add checksums for binary verification
