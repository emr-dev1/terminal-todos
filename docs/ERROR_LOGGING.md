# Error Logging System

## Overview

Comprehensive file-based error logging system that captures all errors, exceptions, and debug information to help diagnose issues.

## Error Log Location

**File Path:** `~/.terminal-todos/data/error.log`

This file is automatically created on first error and contains:
- Full stack traces
- Error context information
- Debug messages (when verbose logging enabled)
- Info messages
- Timestamps for all entries

## How to View Error Logs

### View Recent Errors
```bash
tail -50 ~/.terminal-todos/data/error.log
```

### View Full Log
```bash
cat ~/.terminal-todos/data/error.log
```

### Follow Live Logs
```bash
tail -f ~/.terminal-todos/data/error.log
```

### Search for Specific Errors
```bash
grep "Error in handle_natural_language" ~/.terminal-todos/data/error.log
```

### Clear Old Logs
```bash
rm ~/.terminal-todos/data/error.log
```

## Log Format

Each log entry contains:

```
================================================================================
[2026-01-15 14:23:45] ERROR
================================================================================
Context: Error in handle_natural_language
Exception Type: AttributeError
Exception Message: 'NoneType' object has no attribute 'content'

Full Traceback:
Traceback (most recent call last):
  File "/path/to/app.py", line 1118, in handle_natural_language
    result = await self._call_agent_with_progress(message, chat_log)
  ...
================================================================================
```

## Log Levels

### ERROR
- **When:** Exceptions and failures
- **Contains:** Full stack traces, error context
- **Always logged:** Yes, regardless of VERBOSE_LOGGING setting

### DEBUG
- **When:** Detailed execution flow
- **Contains:** Variable values, state changes
- **Logged when:** VERBOSE_LOGGING=true

### INFO
- **When:** Major operations and milestones
- **Contains:** Operation summaries
- **Logged when:** VERBOSE_LOGGING=true

## Verbose Logging

### Enable Verbose Logging

Add to `.env`:
```
VERBOSE_LOGGING=true
```

### What Gets Logged (Verbose Mode)

**Input Processing:**
- Input submission events
- Input validation
- Command vs natural language detection
- Message history operations

**Agent Execution:**
- Agent invocation with message counts
- Conversation history state
- Tool executions
- Response extraction

**Database Operations:**
- Note creation with metadata
- Vector store sync operations
- Database commits

**Import Operations:**
- Content extraction
- Metadata parsing
- Tag application
- Bulk creation progress

### Example Verbose Log Output

```
================================================================================
[2026-01-15 14:23:45] DEBUG
================================================================================
DEBUG: Input submitted event received
  - input_id: user-input

================================================================================

================================================================================
[2026-01-15 14:23:45] INFO
================================================================================
INFO: Processing user input: list all todos

================================================================================

================================================================================
[2026-01-15 14:23:45] INFO
================================================================================
INFO: Processing natural language: list all todos

================================================================================

================================================================================
[2026-01-15 14:23:46] INFO
================================================================================
INFO: Calling agent (streaming) with 3 messages in history

================================================================================
```

## Error Tracking Locations

Comprehensive error tracking added to:

### 1. Input Submission (`on_input_submitted`)
- Input event reception
- Input bar interaction
- History management
- Command/natural language routing

### 2. Natural Language Handling (`handle_natural_language`)
- Loading state management
- Agent invocation
- Response extraction
- Todo refresh operations

### 3. Agent Invocation (`_call_agent_with_progress`, `_call_agent`)
- Message history management
- Agent graph streaming
- Tool execution tracking
- Response capture

### 4. Import Processing (`_process_import`, `_create_pending_import`)
- Content validation
- Metadata extraction
- Tag application
- Bulk note creation

### 5. Note Service Operations (`create_note_with_metadata`, `create_notes_bulk`)
- Database operations
- Metadata setting
- Vector store sync
- Event logging

## Common Issues and Log Patterns

### Issue: Agent Not Responding

**Look for in logs:**
```
ERROR
Context: Error in handle_natural_language
```

**Possible causes:**
- Agent graph initialization failure
- Message history corruption
- Tool execution failure

### Issue: Import Failing

**Look for in logs:**
```
ERROR
Context: Import processing failed
```

or

```
ERROR
Context: Note creation failed
```

**Possible causes:**
- Database connection issues
- Vector store sync failure
- Invalid metadata format

### Issue: Input Not Processing

**Look for in logs:**
```
ERROR
Context: Error in on_input_submitted
```

**Possible causes:**
- Widget query failures
- Event handler issues
- Input bar state problems

## Debugging Workflow

### Step 1: Enable Verbose Logging
```bash
echo "VERBOSE_LOGGING=true" >> .env
```

### Step 2: Clear Old Logs
```bash
rm ~/.terminal-todos/data/error.log
```

### Step 3: Reproduce Issue
```bash
terminal-todos
# Try the operation that fails
```

### Step 4: Review Logs
```bash
cat ~/.terminal-todos/data/error.log
```

### Step 5: Find Error Context
Look for the last ERROR entry and review the full traceback.

### Step 6: Check Debug Trail
Review the DEBUG/INFO entries leading up to the error to understand execution flow.

## Log File Management

### Automatic Rotation

Currently **not implemented**. The log file grows indefinitely.

### Manual Cleanup

**Clear entire log:**
```bash
rm ~/.terminal-todos/data/error.log
```

**Keep last 1000 lines:**
```bash
tail -1000 ~/.terminal-todos/data/error.log > ~/.terminal-todos/data/error.log.tmp
mv ~/.terminal-todos/data/error.log.tmp ~/.terminal-todos/data/error.log
```

**Archive old logs:**
```bash
mv ~/.terminal-todos/data/error.log ~/.terminal-todos/data/error.log.$(date +%Y%m%d)
```

## Integration with Code

### Logging an Error

```python
from terminal_todos.utils.logger import log_error

try:
    # Your code here
    result = some_operation()
except Exception as e:
    log_error(e, "Description of what failed", show_traceback=True)
    # Handle error...
```

### Logging Debug Info

```python
from terminal_todos.utils.logger import log_debug

log_debug("Operation starting", {
    "param1": value1,
    "param2": value2
})
```

### Logging Info

```python
from terminal_todos.utils.logger import log_info

log_info("User logged in successfully")
```

## Performance Considerations

### File I/O Impact

- Each log write is a file append operation
- Minimal performance impact (< 1ms per log)
- No buffering - logs written immediately

### Disk Space

- Log entries average 500-1000 bytes
- 1000 errors ≈ 500KB - 1MB
- Monitor log file size in production use

### Verbose Mode Impact

- More frequent file writes
- Increased log file growth
- Negligible performance impact on user experience

## Security Considerations

### Sensitive Data

**DO NOT LOG:**
- API keys
- Passwords
- Authentication tokens
- User PII (if applicable)

**Currently logged:**
- User input messages (first 50-100 chars)
- Todo content
- Note titles
- File paths
- Exception messages

### Log File Access

- Stored in user's home directory
- Readable only by the user (default permissions)
- Not transmitted over network

## Future Enhancements

Potential improvements (not implemented):

1. **Automatic Rotation**
   - Max file size limit
   - Keep N old logs
   - Automatic compression

2. **Log Levels Configuration**
   - Fine-grained control
   - Per-module log levels
   - Dynamic level changes

3. **Structured Logging**
   - JSON format
   - Easier parsing
   - Integration with log analysis tools

4. **Remote Logging**
   - Send to logging service
   - Real-time monitoring
   - Aggregation and alerts

5. **Performance Metrics**
   - Operation timing
   - Resource usage
   - Performance bottlenecks

## Support

If you encounter an issue:

1. Enable verbose logging
2. Reproduce the issue
3. Share the relevant error log entries
4. Include app version and environment info

**Log file location:** `~/.terminal-todos/data/error.log`
