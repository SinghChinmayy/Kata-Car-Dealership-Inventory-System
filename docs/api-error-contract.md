# API error contract

Every non-success response has this shape:

```json
{
  "error": {
    "code": "out_of_stock",
    "message": "This vehicle is out of stock.",
    "request_id": "a8b52a68-a21a-4a65-9075-01814d55c63c"
  }
}
```

`request_id` is also returned in the `X-Request-ID` response header. It is a safe correlation identifier for support and logs.

For validation failures only, `fields` is added as a map of field names to safe messages. It never contains submitted values.

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "request_id": "a8b52a68-a21a-4a65-9075-01814d55c63c",
    "fields": {
      "min_price": "Must be less than or equal to max_price."
    }
  }
}
```

## Codes

| Code | Typical status | Meaning |
| --- | --- | --- |
| `validation_error` | 422 | Request data is invalid. |
| `invalid_credentials` | 401 | A login email/password pair is incorrect. |
| `unauthorized` | 401 | An access token is missing, invalid, or expired. |
| `forbidden` | 403 | The authenticated role lacks the required permission. |
| `not_found` | 404 | The requested active resource does not exist. |
| `method_not_allowed` | 405 | The route does not accept the request method. |
| `duplicate_email` | 409 | The registration email already belongs to an account. |
| `out_of_stock` | 409 | The active Vehicle Listing has no purchasable units. |
| `internal_error` | 500 | An unexpected failure occurred; implementation details are not exposed. |
