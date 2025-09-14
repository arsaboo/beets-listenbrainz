# beets-listenbrainz Plugin Development Guide

beets-listenbrainz is a Python plugin for the [beets](https://github.com/beetbox/beets) music library manager that interfaces with ListenBrainz to retrieve personalized playlists and recommendations.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Install the Plugin
- `cd /path/to/beets-listenbrainz`
- `pip install -e .` -- installs plugin in development mode. Takes 15-60 seconds depending on network. NEVER CANCEL - let it complete even if network is slow.
- This installs beets (the main library), the plugin dependencies (requests, musicbrainzngs), and the plugin itself in development mode.

### Install Development Tools
- `pip install flake8 black pytest --user` -- installs linting and testing tools. Takes 30-90 seconds. NEVER CANCEL.
- These tools are not required for basic functionality but are essential for development.

### Configure beets for Testing
- Create beets configuration directory: `mkdir -p ~/.config/beets`
- Create basic config file:
```bash
cat > ~/.config/beets/config.yaml << 'EOF'
plugins: listenbrainz
directory: ~/Music
library: ~/Music/library.db

listenbrainz:
    token: test_token
    username: test_user
EOF
```
- Create music directory: `mkdir -p ~/Music`
- Initialize beets library: `echo "Y" | beet help` -- accepts database creation prompt

### Test Plugin Loading and Basic Functionality
- Verify plugin loads: `beet --help | grep lbupdate` -- should show "lbupdate        Update ListenBrainz views"
- Test plugin command: `beet lbupdate --help` -- should show command usage without errors
- Test plugin import: `python -c "import beetsplug.listenbrainz; print('Plugin imports successfully')"` -- verifies Python syntax

## Development Workflow

### Linting and Code Quality
- Run flake8: `~/.local/bin/flake8 beetsplug/` -- takes ~0.15 seconds. Reports style violations.
- Run black formatter check: `~/.local/bin/black --check beetsplug/` -- takes ~0.15 seconds. Reports formatting issues.
- Fix black formatting: `~/.local/bin/black beetsplug/` -- automatically formats code to standard style.
- **ALWAYS** run linting before committing changes - the current code has known line-length violations that should be fixed for clean commits.

### Testing
- **NOTE**: This repository has no existing test suite. You can create tests using pytest if needed.
- Run basic import test: `python -m py_compile beetsplug/listenbrainz.py` -- verifies syntax correctness.
- Run pytest (if tests exist): `~/.local/bin/pytest` -- currently finds no tests but useful for future test development.

### Manual Testing and Validation
- **CRITICAL**: Always test the plugin with real beets functionality after making changes:
  1. Ensure plugin loads: `echo "Y" | beet --help | grep lbupdate` -- should show "lbupdate        Update ListenBrainz views"
  2. Test command help: `echo "Y" | beet lbupdate --help` -- should show usage without errors
  3. Test plugin import: `python -c "import beetsplug.listenbrainz"`
  4. Verify beets version: `echo "Y" | beet version` -- should show beets version with plugin loaded
- **Note**: Use `echo "Y" |` prefix to auto-accept database creation prompts during testing
- The plugin provides the `lbupdate` command for updating ListenBrainz views, though full functionality requires valid ListenBrainz API credentials.
- Without valid API credentials, the plugin will load and show help but API calls will fail - this is expected behavior for development testing.

## Repository Structure and Key Files

### Core Files
- `setup.py` -- Python package configuration with dependencies: beets>=1.6.0, requests, musicbrainzngs
- `beetsplug/listenbrainz.py` -- Main plugin implementation (175 lines)
- `beetsplug/__init__.py` -- Python package initialization (empty)
- `README.md` -- Installation and configuration instructions
- `.gitignore` -- Standard Python gitignore with build artifacts, virtual environments, etc.

### Plugin Functionality
The plugin provides:
- `ListenBrainzPlugin` class that extends BeetsPlugin
- `lbupdate` command for interfacing with ListenBrainz API
- Methods for fetching weekly playlists (exploration and jams) from ListenBrainz
- Integration with MusicBrainz for track metadata

### Configuration Requirements
The plugin requires ListenBrainz API credentials in beets config:
```yaml
listenbrainz:
    token: listenbrainz_token  # API token from ListenBrainz
    username: listenbrainz_user  # ListenBrainz username
```

## Common Tasks and Expected Timings

### Installation and Setup (First Time)
1. `pip install -e .` -- 15-60 seconds depending on network speed. NEVER CANCEL.
2. Install dev tools: `pip install flake8 black pytest --user` -- 30-90 seconds. NEVER CANCEL.
3. Configure beets and create directories -- instant
4. Test plugin loading -- 2-3 seconds

### Development Cycle
1. Make code changes to `beetsplug/listenbrainz.py`
2. Test syntax: `python -m py_compile beetsplug/listenbrainz.py` -- instant
3. Run linting: `~/.local/bin/flake8 beetsplug/` -- ~0.15 seconds
4. Test plugin import: `python -c "import beetsplug.listenbrainz"` -- instant  
5. Test beets integration: `echo "Y" | beet lbupdate --help` -- 2-3 seconds
6. Verify plugin loads: `echo "Y" | beet version` -- should show plugin in loaded plugins

### Before Committing
1. `~/.local/bin/flake8 beetsplug/` -- check for style violations
2. `~/.local/bin/black beetsplug/` -- auto-format code
3. `python -c "import beetsplug.listenbrainz"` -- verify imports work
4. `echo "Y" | beet lbupdate --help` -- verify beets integration works
5. `echo "Y" | beet version` -- verify plugin loads correctly

## Network Dependencies and Limitations
- Installation requires internet access to download dependencies from PyPI
- Plugin functionality requires ListenBrainz API access (api.listenbrainz.org)
- Plugin uses MusicBrainz API for metadata (requires internet)
- Development tools work offline once installed

## Troubleshooting
- If `pip install` fails with timeout: Wait for completion, don't cancel. Network issues are temporary.
- If plugin doesn't load: Check beets config has `plugins: listenbrainz` and config file is in `~/.config/beets/config.yaml`
- If import fails: Verify plugin was installed with `pip install -e .`
- If linting tools not found: Install with `pip install flake8 black pytest --user` and use `~/.local/bin/` prefix

## Repository State
- No existing CI/CD pipelines (no `.github/workflows/`)
- No existing test suite
- Standard Python project structure
- Dependencies are minimal and stable (beets, requests, musicbrainzngs)
- Code has some style violations (line length) that should be addressed when making changes