# GitHub Copilot Instructions for beets-listenbrainz

## Overview
This is a **beets plugin** that provides integration with **ListenBrainz**, a music listening tracking service. The plugin allows users to interact with ListenBrainz playlists and track data through the beets music library manager.

## Project Structure
```
beets-listenbrainz/
├── beetsplug/
│   ├── __init__.py          # Plugin package initialization
│   └── listenbrainz.py      # Main plugin implementation
├── setup.py                 # Package configuration
├── README.md               # Project documentation
└── .github/
    └── copilot-instructions.md
```

## Core Technologies & Dependencies
- **beets**: Music library manager framework (>=1.6.0)
- **requests**: HTTP client for ListenBrainz API calls
- **musicbrainzngs**: MusicBrainz API client for track metadata
- **Python 3.x**: Primary development language

## Plugin Architecture
This follows the standard **beets plugin pattern**:
- Extends `BeetsPlugin` base class
- Implements `commands()` method to add CLI commands
- Uses beets config system for user settings
- Integrates with beets UI and logging systems

## Key Components

### ListenBrainzPlugin Class
- **Main plugin class** that handles all ListenBrainz interactions
- **Configuration**: Reads `token` and `username` from beets config
- **Authentication**: Uses token-based auth with ListenBrainz API
- **Commands**: Provides `lbupdate` command for syncing data

### API Integration
- **Base URL**: `http://api.listenbrainz.org/1/`
- **Authentication**: Bearer token in Authorization header
- **Key endpoints**:
  - `/user/{username}/playlists/createdfor` - Get user playlists
  - `/playlist/{identifier}` - Get specific playlist
  - Uses MusicBrainz for track metadata enrichment

### Data Processing
- **Playlist Types**: Handles "Exploration" and "Jams" playlists
- **Date Parsing**: Extracts dates from playlist titles (format: "week of YYYY-MM-DD")
- **Track Enhancement**: Enriches playlist tracks with MusicBrainz metadata
- **Sorting**: Orders playlists by type and date (most recent first)

## Development Guidelines

### Code Style
- Follow **Python naming conventions** (snake_case for functions/variables)
- Use **descriptive method names** that indicate purpose
- Include **docstrings** for public methods
- Handle **exceptions gracefully** with proper logging

### Error Handling
- Use `self._log.debug()` for debugging information
- Catch `requests.exceptions.RequestException` for API errors
- Return `None` for failed API requests
- Validate data structures before processing

### Configuration
- All user settings go through beets config system
- Mark sensitive data (tokens) as `redact = True`
- Provide helpful error messages for missing config

### Testing Considerations
- Mock external API calls (ListenBrainz, MusicBrainz)
- Test configuration loading and validation
- Verify command registration and execution
- Test data processing and filtering logic

## Common Patterns

### API Request Pattern
```python
def _make_request(self, url):
    try:
        response = requests.get(
            url=url,
            headers=self.AUTH_HEADER,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        self._log.debug(f"Request failed: {e}")
        return None
```

### Beets Command Pattern
```python
def commands(self):
    cmd = ui.Subcommand("commandname", help="Description")
    def func(lib, opts, args):
        items = lib.items(ui.decargs(args))
        # Process items
    cmd.func = func
    return [cmd]
```

### Data Processing Pattern
```python
# Filter and sort data
filtered_data = [item for item in data if condition(item)]
sorted_data = sorted(filtered_data, key=lambda x: x["date"], reverse=True)
```

## Development Environment Setup

### Installation
1. Install beets: `pip install beets>=1.6.0`
2. Install plugin dependencies: `pip install requests musicbrainzngs`
3. Install in development mode: `pip install -e .`

### Configuration
Add to beets `config.yaml`:
```yaml
plugins: listenbrainz
listenbrainz:
    token: your_listenbrainz_token
    username: your_username
```

### Testing Commands
```bash
# Test plugin import
python -c "from beetsplug.listenbrainz import ListenBrainzPlugin"

# Test beets command (requires valid config)
beet lbupdate
```

## Contributing Guidelines

### When Adding New Features
- Follow existing API request patterns
- Add proper error handling and logging
- Update docstrings and comments
- Consider configuration options
- Test with different data scenarios

### When Fixing Bugs
- Identify the root cause first
- Add logging to understand data flow
- Test edge cases (empty responses, network errors)
- Verify fix doesn't break existing functionality

### API Integration
- Always use timeouts for HTTP requests
- Handle rate limiting gracefully  
- Cache responses when appropriate
- Validate API response structure before processing

## Security Considerations
- Never log authentication tokens
- Use `config.redact = True` for sensitive fields
- Validate all external data inputs
- Use HTTPS for API communications

## Performance Tips
- Batch API requests when possible
- Cache frequently accessed data
- Use appropriate timeouts
- Minimize MusicBrainz API calls (they're rate limited)

## Common Issues & Solutions

### Authentication Failures
- Verify token is valid and not expired
- Check username matches token owner
- Ensure proper Authorization header format

### API Rate Limiting
- Implement exponential backoff
- Cache responses appropriately  
- Batch requests when possible

### Data Processing Errors
- Validate API response structure
- Handle missing or malformed data gracefully
- Log detailed error information for debugging

## Files to Focus On
- `beetsplug/listenbrainz.py` - Main plugin logic
- `setup.py` - Package dependencies and metadata
- User's beets `config.yaml` - Plugin configuration

This plugin bridges two complex systems (beets and ListenBrainz), so understanding both ecosystems is helpful for effective development.