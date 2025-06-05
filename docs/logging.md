# Logging Best Practices

## Overview

This document provides guidelines for implementing logging in the UCG_v2 application.

## Core Principles

1. **Use the proper logging level**:
   - `DEBUG`: Detailed information, typically useful only for diagnosing problems
   - `INFO`: Confirmation that things are working as expected
   - `WARNING`: Indication that something unexpected happened, or may happen in the near future
   - `ERROR`: Due to a more serious problem, the software was unable to perform a function
   - `CRITICAL`: A serious error indicating the program itself may be unable to continue running

2. **Include context**:
   - Always provide enough context to understand what operation was being attempted
   - Include relevant IDs (event_id, student_id, etc.)
   - For user-facing errors, consider including a user-friendly message

3. **Handle exceptions properly**:
   - Always catch exceptions at the appropriate level
   - Log the exception with sufficient context
   - Consider using `exc_info=True` for full stack traces on errors

## Implementation

### Using the Logger in Route Handlers

Replace print statements with logger calls:

```python
# AVOID
try:
    # code that might fail
except Exception as e:
    print(f"Error: {str(e)}")

# RECOMMENDED
from utils.logger import get_logger
logger = get_logger(__name__)

try:
    # code that might fail
except Exception as e:
    logger.error(f"Failed to process data: {str(e)}", exc_info=True)
```

### Standardized Error Handling

For client routes, use the standardized error handling utilities:

```python
from routes.client.client_logging import handle_route_exception

@router.get("/some-route")
async def some_route(request: Request):
    try:
        # Route implementation
        return templates.TemplateResponse(...)
    except Exception as e:
        return handle_route_exception(
            request, 
            e, 
            "some_route", 
            "client/error_template.html",
            {"context_variable": value}
        )
```

## Configuration

Logging is configured in `utils/logger.py` and initialized in `main.py`. Logs are stored in the `logs/` directory:

- Console: All logs of INFO level and above
- File (`logs/app.log`): All logs of WARNING level and above with detailed context
