# Handling Concurrent Calls

## Overview

This solution is designed to handle **multiple concurrent calls** efficiently. When multiple callers dial the ACS (Azure Communication Services) phone number simultaneously, the system can process each call independently and concurrently.

## Architecture for Concurrency

### 1. Stateless Design

The application is built with a **stateless architecture**, which is essential for handling concurrent calls:

- **Independent Handler Instances**: Each incoming call (via WebSocket) creates a new `ACSMediaHandler` instance with its own:
  - Unique `connection_id` for tracking
  - Dedicated WebSocket connection to Azure Voice Live API
  - Independent audio processing queues
  - Separate conversation transcript and session state
  - Isolated tool registry

- **No Shared State**: Handlers do not share state between calls, preventing race conditions and ensuring call isolation.

### 2. Connection Flow for Concurrent Calls

When multiple people dial the ACS number in parallel, here's what happens:

```
Caller 1 → ACS → IncomingCall Event → Answer Call → WebSocket 1 → Handler 1 → Voice Live Session 1
Caller 2 → ACS → IncomingCall Event → Answer Call → WebSocket 2 → Handler 2 → Voice Live Session 2
Caller 3 → ACS → IncomingCall Event → Answer Call → WebSocket 3 → Handler 3 → Voice Live Session 3
```

Each call follows this independent flow:

1. **Incoming Call Event**: ACS sends an `IncomingCall` event via EventGrid to `/acs/incomingcall`
2. **Call Answer**: The system answers the call with media streaming configuration pointing to the WebSocket endpoint
3. **WebSocket Connection**: ACS establishes a unique WebSocket connection to `/acs/ws` with caller information
4. **Handler Creation**: A new `ACSMediaHandler` instance is created for this specific call
5. **Voice Live Connection**: The handler establishes its own WebSocket connection to Azure Voice Live API
6. **Concurrent Processing**: Audio streams are processed independently in parallel

### 3. Connection Tracking

The system includes a **ConnectionManager** that tracks all active connections:

- **Thread-safe tracking**: Uses async locks to safely manage concurrent connection registration/unregistration
- **Connection limits**: Configurable maximum concurrent connections (default: 100)
- **Connection metadata**: Tracks connection ID, caller ID, connection type, and connection time
- **Automatic cleanup**: Connections are automatically unregistered when the call ends

### 4. Horizontal Scaling

The infrastructure is configured to scale horizontally:

- **Azure Container Apps**: The application runs on Azure Container Apps with auto-scaling enabled
- **Scaling Configuration** (in `infra/modules/containerapp.bicep`):
  ```bicep
  scale: {
    minReplicas: 1
    maxReplicas: 10
    rules: [
      {
        name: 'http-scaler'
        http: {
          metadata: {
            concurrentRequests: '100'
          }
        }
      }
    ]
  }
  ```
- **Resource Allocation**: Each container gets 2.0 CPU cores and 4.0 GB memory

### 5. Connection Limits and Capacity

#### Per-Instance Limits
- **Max Concurrent Connections**: 100 (configurable in `ConnectionManager`)
- **WebSocket Connections**: Each call requires 2 WebSocket connections:
  - 1 from ACS to the application
  - 1 from the application to Voice Live API

#### Cluster-Wide Capacity
- With 10 replicas and 100 connections per instance: **1,000 concurrent calls**
- Can be scaled further by:
  - Increasing `maxReplicas` in the Bicep configuration
  - Increasing `max_connections` in the `ConnectionManager`

## Monitoring Concurrent Calls

### Health Check Endpoint

Check the system health and active connection count:

```bash
curl https://<your-app-url>/health
```

Response:
```json
{
  "status": "healthy",
  "active_connections": 5,
  "max_connections": 100
}
```

### Statistics Endpoint

Get detailed statistics about all active connections:

```bash
curl https://<your-app-url>/stats
```

Response:
```json
{
  "status": "healthy",
  "active_connections": 5,
  "max_connections": 100,
  "connection_types": {
    "acs": 3,
    "web": 2
  },
  "connections": [
    {
      "connection_id": "a1b2c3d4-...",
      "caller_id": "+1234567890",
      "type": "acs",
      "connected_at": "2025-12-05T10:45:00Z",
      "status": "connected"
    }
  ]
}
```

### Logging

The system logs key events for each connection:

- **Connection Registration**: When a new call connects
  ```
  Connection registered: <connection_id> (type=acs, caller=+1234567890). Active connections: 5/100
  ```

- **Connection Unregistration**: When a call ends
  ```
  Connection unregistered: <connection_id> (duration=120.5s). Active connections: 4/100
  ```

- **Voice Live Connection**: When connecting to Voice Live API
  ```
  [connection_id=<id>] Connected to Voice Live API for caller_id=+1234567890
  ```

## Testing Concurrent Calls

### Manual Testing

To test concurrent call handling:

1. **Setup**: Ensure your application is deployed and the ACS phone number is configured
2. **Simulate**: Have multiple people call the ACS number simultaneously
3. **Monitor**: Watch the logs and check the `/stats` endpoint to see active connections
4. **Verify**: Each caller should have an independent conversation without interference

### Load Testing

For systematic load testing:

```bash
# Monitor stats while generating load
while true; do
  curl https://<your-app-url>/stats
  sleep 5
done
```

## Error Handling

### Connection Limit Reached

If the connection limit is reached, new callers will receive an error:

```
Failed to register connection <connection_id> - connection limit reached
```

**Resolution**: 
- Increase `max_connections` in `ConnectionManager`
- Scale horizontally by increasing `maxReplicas` in the infrastructure

### Resource Exhaustion

Monitor Azure Container Apps metrics for:
- CPU usage
- Memory usage
- Active connections

If resources are exhausted, the auto-scaler will create additional replicas (up to `maxReplicas`).

## Best Practices

1. **Monitor Regularly**: Check `/health` and `/stats` endpoints to understand usage patterns
2. **Set Appropriate Limits**: Configure `max_connections` based on your Azure resources and expected load
3. **Plan for Scale**: Ensure Azure quotas allow for the expected number of replicas
4. **Test Under Load**: Regularly test with multiple concurrent calls to verify behavior
5. **Review Logs**: Use Azure Monitor/Application Insights to track connection patterns and errors

## Architecture Benefits

1. **Isolation**: Each call is completely isolated with no shared state
2. **Scalability**: Horizontal scaling allows handling thousands of concurrent calls
3. **Reliability**: Failed calls don't affect other active calls
4. **Observability**: Detailed logging and monitoring endpoints
5. **Resource Efficiency**: Automatic scaling based on actual load

## Limitations and Considerations

1. **Azure Service Limits**: 
   - Voice Live API has its own rate limits
   - ACS has connection and throughput limits
   - Verify quotas for your subscription

2. **Network Bandwidth**: Each call requires bidirectional audio streaming
   - Estimate ~100 KB/s per call
   - Plan network capacity accordingly

3. **Cost**: Each concurrent call consumes:
   - Voice Live API usage (per-second pricing)
   - ACS call automation usage
   - Container Apps compute resources

4. **WebSocket Connections**: Each call uses 2 WebSocket connections, which count against system limits

## Summary

This solution is **fully capable of handling concurrent calls** through:
- Stateless architecture with independent handler instances
- Connection tracking and management
- Horizontal auto-scaling
- Comprehensive monitoring and logging

The system can scale from single calls to hundreds or thousands of concurrent calls by adjusting the configuration and infrastructure limits.
