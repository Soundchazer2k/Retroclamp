# AI Debug Logging Guidelines

**Audience:** AI code assistant, application developers, and AI-assisted coders

---

## 1. Why Logging Matters

- **Real-time Visibility:** Logs provide insight into application behavior as it runs, enabling early detection of errors and performance bottlenecks.
  (edgedelta.com, coralogix.com)

- **Debugging Aid:** Detailed logs help trace execution flow and pinpoint root causes of failures.
  (edgedelta.com, last9.io)

- **Audit & Compliance:** Accurate logging records are often required for regulatory audits and forensic investigations.
  (edgedelta.com)

---

## 2. Core Principles of Effective Logging

- **Consistent Format:** Use a uniform template (timestamp, level, module, message) for all log entries to simplify parsing and analysis.
  (edgedelta.com)

- **Appropriate Log Levels:** Assign levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) according to severity and environment (development vs. production).
  (edgedelta.com)

- **Contextual Information:** Enrich logs with metadata (user IDs, transaction IDs, session IDs) to correlate events across distributed components.
  (edgedelta.com)

- **Avoid Sensitive Data:** Never log passwords, tokens, or personal identifiers. Implement masking or redaction as needed.
  (edgedelta.com)

- **Structured Logging:** Leverage JSON or key/value formats to make logs machine-readable for systems like ELK or Splunk.
  (edgedelta.com, coralogix.com)

---

## 3. Recommended Setup Pattern

```python
import logging
import logging.config

# 1. Load configuration from a dict or file
logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s [%(name)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'INFO'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG'
        }
    }
})

logger = logging.getLogger(__name__)
```

- Use `logging.getLogger(__name__)` in each module to maintain a clear hierarchy and control.
  (coralogix.com)

- Configure as early as possible in application entry point to ensure consistency.
  (last9.io)

---

## 4. Handling Errors and Exceptions

- Use `logger.exception()` inside exception handlers to automatically include stack traces.
  (last9.io)

- Log at `ERROR` or `CRITICAL` level for unhandled exceptions to trigger alerts.
  (edgedelta.com)

- Include contextual extras for failed operations:

  ```python
  logger.error('Payment failed', extra={'user_id': uid, 'order_id': oid})
  ```

  (last9.io)

---

## 5. Performance Considerations

- **Lazy Message Construction:** Use %-style formatting or passing arguments to avoid expensive f-string evaluation when logs are disabled.
  (coralogix.com, last9.io)

- **Avoid Blocking Handlers:** Offload heavy I/O to background threads using `QueueHandler` and `QueueListener`.
  (coralogix.com)

- **Sampling & Rate Limiting:** For high-volume events, sample a subset (e.g., 10%) to control log volume.
  (last9.io)

---

## 6. Operational Practices

- **Log Rotation & Retention:** Employ `RotatingFileHandler` or `TimedRotatingFileHandler` to manage disk usage.
  (edgedelta.com, last9.io)

- **Centralized Aggregation:** Forward logs to a central system (ELK, Graylog, Splunk) for unified search and alerting.
  (edgedelta.com)

- **Automated Alerts:** Configure alerts on `ERROR` or `CRITICAL` events via email, Slack, or pager systems.
  (edgedelta.com)

- **Regular Review & Tuning:** Periodically refine log levels and alert thresholds to reduce noise.
  (edgedelta.com)

---

## 7. Additional Resources

- Real Python: [Python Logging Tutorial](https://realpython.com/python-logging/)

- Python Logging Cookbook: [Official Recipes](https://docs.python.org/3/howto/logging-cookbook.html)

- Coralogix Deep Dive: [Ultimate Guide](https://coralogix.com/)

- Last9 Practical Tips: [Ultimate Guide](https://last9.io/)

- EdgeDelta Best Practices: [Python Logging Guide](https://edgedelta.com/)

---

> Adopt these guidelines to ensure that AI-generated logging code is consistent, informative, and performance-conscious across all projects.
