# Risk Manager V6

Real-time trade risk management system for Topstep Trading.

## Walking Skeleton - Authentication

This is the first step of the walking skeleton implementation, focusing on authentication.

### Setup

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Set environment variables:**
   Create a `.env` file in the project root with:
   ```
   TOPSTEP_USERNAME=your_username_here
   TOPSTEP_API_KEY=your_api_key_here
   ```

3. **Run the application:**
   ```bash
   python run.py
   ```

### Expected Output

When successful, you should see:
```
✅ Authenticated (token expires in 58 min)
✅ Token validation working
```

### Logs

The application uses structured logging. You'll see JSON-formatted logs like:
```json
{"event": "Risk Manager V6 starting up", "timestamp": "2024-01-01T12:00:00Z", "level": "info"}
{"event": "Attempting authentication", "timestamp": "2024-01-01T12:00:00Z", "level": "info"}
{"event": "Authentication successful", "token_expires_in_minutes": 58, "timestamp": "2024-01-01T12:00:00Z", "level": "info"}
```

### Architecture

This walking skeleton implements:
- **Configuration**: YAML config + environment variables
- **Logging**: Structured JSON logging with structlog
- **HTTP Client**: Session management with retry logic
- **Authentication**: JWT token management with auto-refresh
- **Error Handling**: Custom exceptions for different error types

### Next Steps

Once authentication is working, the next steps will be:
1. Fetch account data
2. Persist data to local storage
3. Implement risk calculations
4. Add decision logic

