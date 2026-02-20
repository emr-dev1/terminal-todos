# Arize Tracing for Terminal Todos

This document explains how to set up Arize tracing to monitor and debug your Terminal Todos LangGraph agent in production.

## What is Arize Tracing?

Arize is a production-grade observability platform that allows you to:
- **Trace LLM calls**: See every request/response to OpenAI with full context
- **Monitor tool executions**: Watch your agent call tools in real-time
- **Debug agent reasoning**: Understand the agent's decision-making process
- **Track token usage**: Monitor costs and performance across all sessions
- **Analyze failures**: Identify and fix errors quickly with full stack traces
- **Production monitoring**: Monitor your agent in production environments

## Installation

Dependencies are already included in `pyproject.toml`. Install them with:

```bash
pip install -e .
```

This installs:
- `openinference-instrumentation-langchain` - LangChain/LangGraph automatic instrumentation
- `arize-otel` - Arize OpenTelemetry convenience functions
- `opentelemetry-sdk` - OpenTelemetry SDK
- `opentelemetry-exporter-otlp` - OTLP exporter for sending traces

## Setup

### 1. Sign Up for Arize

1. Go to https://arize.com
2. Sign up for a free account
3. Once logged in, navigate to the dashboard
4. Get your credentials:
   - **Space ID**: Found in Space Settings
   - **API Key**: Found in Space Settings → API Keys

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Enable Arize Tracing
ENABLE_ARIZE_TRACING=true

# Your Arize credentials
ARIZE_SPACE_ID=your-space-id-here
ARIZE_API_KEY=your-api-key-here

# Optional: Custom project name
ARIZE_PROJECT_NAME=terminal-todos
```

### 3. Run Terminal Todos

```bash
terminal-todos
```

You should see:
```
✓ Arize tracing initialized
  Project: terminal-todos
  Space ID: abcd1234...
```

### 4. View Traces

1. Open https://app.arize.com in your browser
2. Navigate to your project/space
3. Go to "Traces" section
4. Interact with the agent (ask questions, create todos, etc.)
5. Watch traces appear in real-time in the Arize dashboard

## Configuration Options

### Environment Variables

```bash
# Required: Enable tracing
ENABLE_ARIZE_TRACING=true

# Required: Arize Space ID (from Arize dashboard)
ARIZE_SPACE_ID=your-space-id-here

# Required: Arize API Key (from Arize dashboard)
ARIZE_API_KEY=your-api-key-here

# Optional: Project name (default: terminal-todos)
ARIZE_PROJECT_NAME=terminal-todos
```

### Programmatic Configuration

Edit `src/terminal_todos/config.py`:

```python
enable_arize_tracing: bool = True  # Enable by default
arize_space_id: str = "your-space-id"
arize_api_key: str = "your-api-key"
arize_project_name: str = "terminal-todos"
```

## What Gets Traced?

Arize automatically captures:

### 1. **LLM Calls**
- Model name (gpt-4o, etc.)
- Full prompt and completion
- Token counts (input/output/total)
- Latency and performance metrics
- Temperature and other parameters
- Cost estimates

### 2. **Tool Executions**
- Tool name (e.g., `create_todo`, `search_notes`, `extract_todos_from_notes`)
- Input parameters with full context
- Output/results
- Execution time
- Success/failure status
- Error messages and stack traces

### 3. **Agent Flow**
- Full conversation history across sessions
- Reasoning steps and decisions
- Tool selection logic
- State transitions in the LangGraph
- Conditional edge decisions

### 4. **Errors and Exceptions**
- Full exception traces
- Failed tool calls with context
- LLM errors and retries
- Timeouts and rate limits

### 5. **Performance Metrics**
- End-to-end latency
- Token usage per conversation
- Cost per session
- Tool execution times
- Agent step durations

## Use Cases

### Debugging Agent Behavior

**Problem**: Agent isn't extracting todos correctly from notes

**Solution**:
1. Enable AX tracing
2. Run the extraction: `"extract todos from note 14"`
3. Open Arize dashboard
4. Click on the trace
5. See exactly:
   - What prompt was sent to the LLM
   - What the LLM returned
   - Which tools were called and with what parameters
   - Where the failure occurred
   - Full context of the conversation

### Optimizing Token Usage & Cost

**Problem**: High OpenAI costs

**Solution**:
1. Enable AX tracing for a few days
2. Go to Arize dashboard → Analytics
3. View token usage by:
   - Query type
   - Tool used
   - Time of day
   - User session
4. Identify expensive queries and optimize
5. Set up alerts for unusual spending

### Production Monitoring

**Problem**: Need to monitor agent in production

**Solution**:
1. Enable AX tracing in production environment
2. Monitor traces remotely from Arize dashboard
3. Set up alerts for:
   - High latency (>5 seconds)
   - Errors and failures
   - Unusual token usage
   - Tool execution failures
4. Review daily/weekly reports

### Quality Assurance

**Problem**: Need to ensure agent responses are high quality

**Solution**:
1. Use Arize's built-in LLM evaluations
2. Automatically score traces for:
   - Relevance
   - Hallucination detection
   - Toxicity
   - Custom metrics
3. Review low-scoring traces
4. Improve prompts and tool implementations

## Advanced Features

### Custom Metadata

Add custom metadata to traces:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("user_id", "user123")
    span.set_attribute("session_type", "todo_extraction")
    # Your code here
```

### Filtering Traces

In the Arize dashboard, you can filter traces by:
- Date range
- Latency
- Token usage
- Tool used
- Success/failure
- Custom attributes

### Alerts

Set up alerts in Arize for:
- Error rate exceeds threshold
- Latency exceeds threshold
- Token usage exceeds budget
- Specific tool failures

## Performance Impact

Arize tracing has minimal performance impact:
- **Latency**: +5-10ms per LLM call (async instrumentation)
- **Memory**: Negligible (traces sent asynchronously)
- **CPU**: <1% overhead
- **Network**: Traces batched and compressed

For production, tracing is safe to leave enabled continuously.

## Disabling Tracing

To disable tracing:

```bash
# .env
ENABLE_ARIZE_TRACING=false
```

Or remove the environment variable. The agent will work normally without any performance impact.

## Troubleshooting

### Traces Not Appearing

1. **Check credentials**: Verify `ARIZE_SPACE_ID` and `ARIZE_API_KEY` are correct
2. **Check environment**: Ensure `ENABLE_ARIZE_TRACING=true`
3. **Check startup message**: Look for "✓ Arize tracing initialized"
4. **Check Arize dashboard**: Traces may take 30-60 seconds to appear
5. **Check network**: Ensure your machine can reach `app.arize.com`

### Import Errors

```bash
# If you see "ModuleNotFoundError: No module named 'openinference'"
pip install openinference-instrumentation-langchain
```

### Authentication Errors

If you see authentication errors:
1. Verify your Space ID and API Key in Arize dashboard
2. Ensure no extra spaces or quotes in `.env` file
3. Check that keys haven't expired
4. Verify your Arize account is active

### No Traces for Certain Operations

Some operations may not generate traces if:
- They don't involve LLM calls
- They're simple database operations
- They're UI interactions only

To trace custom operations, add manual instrumentation (see Advanced Features).

## Data Privacy

Arize traces include:
- Full LLM prompts and completions
- Tool inputs and outputs
- User messages

**Important**: Do not enable tracing if your data contains:
- Sensitive personal information (PII)
- Confidential business data
- Credentials or API keys

Or use Arize's data scrubbing features to redact sensitive information.

## Cost

Arize pricing:
- **Free tier**: Up to 1,000 traces/month
- **Pro tier**: Pay-as-you-go for additional traces
- **Enterprise**: Custom pricing for high volume

Check current pricing at: https://arize.com/pricing

## Links

- **Arize Dashboard**: https://app.arize.com
- **Arize Documentation**: https://docs.arize.com
- **LangGraph Integration**: https://arize.com/docs/ax/integrations/python-agent-frameworks/langgraph/langgraph-tracing
- **OpenInference Spec**: https://github.com/Arize-ai/openinference

## Support

For issues with:
- **Terminal Todos**: Open GitHub issue
- **Arize**: Visit https://docs.arize.com or contact support@arize.com
