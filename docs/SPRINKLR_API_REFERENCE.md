# Sprinklr API Reference (READ-ONLY)

> **⚠️ CRITICAL: READ-ONLY ACCESS ONLY**
>
> This project has READ-ONLY access to Sprinklr.
>
> **PERMITTED:** GET requests, POST requests that search/fetch data
>
> **FORBIDDEN:** Any CREATE, UPDATE, or DELETE operations

---

## Authentication

```
Authorization: Bearer {SPRINKLR_ACCESS_TOKEN}
Key: {SPRINKLR_API_KEY}
Content-Type: application/json
Accept: application/json
```

## Base URLs

| Purpose | URL |
|---------|-----|
| Primary | `https://api2.sprinklr.com/{env}/` |
| Search/Reports/Bulk | `https://api3.sprinklr.com/{env}/` |

**Environments:** `{env}` = `prod`, `prod2`, `prod3`, `prod4`, `prod8`, etc.

API keys are environment-specific. A key generated for one environment will not work on another.

## Token Management

- Access tokens expire after a set time
- Use refresh token to obtain new access token without re-authenticating
- Same API key and token work for both v1 and v2 endpoints

---

# Case API (READ-ONLY)

## GET Case by Case Number

```
GET https://api3.sprinklr.com/{env}/api/v2/case/case-numbers?case-number={caseNumber}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Internal case ID |
| `caseNumber` | Integer | Human-readable case number |
| `subject` | String | Case subject |
| `description` | String | Case description |
| `status` | String | Case state (Open, Pending, Closed) |
| `priority` | String | Urgency level |
| `caseType` | String | Type (Problem, Incident, Task) |
| `createdTime` | Integer | Creation time (epoch ms) |
| `modifiedTime` | Integer | Last modified (epoch ms) |
| `firstMessageId` | String | First associated message ID |
| `dueDate` | Integer | Due date (epoch ms) |
| `sentiment` | Integer | Sentiment score |
| `workflow` | Object | Workflow data (see below) |
| `contact` | Object | Contact info (`id`, `name`, `channelType`) |
| `externalCase` | Object | External system linkage |

**Workflow Object:**

| Field | Description |
|-------|-------------|
| `workflow.assignment.assigneeId` | Assigned user ID |
| `workflow.assignment.assigneeType` | USER or BOT |
| `workflow.customProperties` | Custom field values (key: field ID, value: array) |
| `workflow.queues[].queueId` | Queue ID |
| `workflow.queues[].assignmentTime` | Assignment time (epoch ms) |

---

## GET Case Associated Messages

```
GET https://api3.sprinklr.com/{env}/api/v2/case/associated-messages?id={caseId}
```

With cursor (messages after timestamp):
```
GET https://api3.sprinklr.com/{env}/api/v2/case/associated-messages?id={caseId}&cursor={epochTime}
```

**Response:** Array of message ID strings

---

# Message API (READ-ONLY)

## POST Bulk Fetch Messages

```
POST https://api3.sprinklr.com/{env}/api/v2/message/bulk-fetch
Content-Type: application/json

["messageId1", "messageId2", "messageId3"]
```

**Message ID Format:**
```
{sourceType}_{sourceId}_{channelCreatedTime}_{channelType}_{messageType}_{channelMessageId}
```
- `sourceType`: ACCOUNT, PERSISTENT_SEARCH, LISTENING
- `sourceId`: Account ID or PS ID
- `channelCreatedTime`: Epoch timestamp
- `channelType`: TWITTER, FACEBOOK, INSTAGRAM, etc.
- `messageType`: See Message Type Codes below

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `messageId` | String | Unique message identifier |
| `sourceType` | String | ACCOUNT, PERSISTENT_SEARCH, LISTENING |
| `sourceId` | String | Account or PS ID |
| `content.text` | String | Message text |
| `content.title` | String | Message title (if any) |
| `content.attachment` | Object | Attachment info (url, type, previewUrl) |
| `channelType` | String | Channel (TWITTER, FACEBOOK, etc.) |
| `channelCreatedTime` | Epoch | Time on native channel |
| `createdTime` | Epoch | Time in Sprinklr |
| `modifiedTime` | Epoch | Last modified |
| `brandPost` | Boolean | True if from brand account |
| `language` | String | Language code (en, es, fr, etc.) |
| `senderProfile` | Object | Sender details |
| `receiverProfile` | Object | Receiver details |
| `enrichments.sentiment` | Integer | Sentiment (-1, 0, 1) |
| `workflow.customProperties` | Object | Custom field values |
| `parentMessageId` | String | Parent message (for replies) |
| `conversationMessageId` | String | Conversation thread ID |

**Profile Object (sender/receiver):**

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Display name |
| `username` | String | Handle/username |
| `channelType` | String | Channel type |
| `channelId` | String | Channel user ID |
| `permalink` | URL | Profile URL |
| `avatarUrl` | String | Profile picture URL |
| `followers` | Integer | Follower count |
| `following` | Integer | Following count |
| `verified` | Boolean | Verified status |

---

# Search API (READ-ONLY)

## POST Search by Entity

```
POST https://api3.sprinklr.com/{env}/api/v2/search/{entityType}
```

**Entity Types:** `CASE`, `MESSAGE`, `PROFILE`, `USER`, `CAMPAIGN`, `TASK`, `COMMENT`, `CUSTOM_FIELD`

**Request Body:**

```json
{
  "filter": {
    "type": "AND",
    "filters": [
      {"type": "EQUALS", "key": "deleted", "values": [false]},
      {"type": "GTE", "key": "createdTime", "values": [1704067200000]}
    ]
  },
  "sorts": [{"key": "createdTime", "order": "DESC"}],
  "page": {"start": 1, "size": 100},
  "includeCount": true
}
```

**Response:**
```json
{
  "data": {
    "results": [...],
    "cursor": "id=xxx",
    "totalCount": 1234
  },
  "errors": []
}
```

## GET Search by Cursor (Pagination)

```
GET https://api3.sprinklr.com/{env}/api/v2/search/{entityType}?id={cursorId}
```

**Note:** Cursor expires after 5 minutes.

---

## Filter Types

| Type | Description |
|------|-------------|
| `AND` | All conditions must match |
| `OR` | Any condition must match |
| `NOT` | Negates conditions |
| `IN` | Key matches any value in list |
| `NIN` | Key matches none in list |
| `EQUALS` | Exact match |
| `NOT_EQUALS` | Not equal |
| `GT` | Greater than |
| `GTE` | Greater than or equal |
| `LT` | Less than |
| `LTE` | Less than or equal |
| `CONTAINS` | Contains substring |

---

## CASE Filter Keys

| Key | Supported Types |
|-----|-----------------|
| `id` | IN, NIN, EQUALS, NOT_EQUALS, LT, LTE, GT, GTE |
| `caseNumber` | IN, NIN, EQUALS, NOT_EQUALS, LT, LTE, GT, GTE |
| `createdTime` | LT, LTE, GT, GTE, EQUALS |
| `modifiedTime` | IN, NIN, EQUALS, NOT_EQUALS, LT, LTE, GT, GTE |
| `deleted` | EQUALS, NOT_EQUALS |
| `workflow.customProperties.{fieldId}` | IN, NIN, EQUALS, NOT_EQUALS |
| `workflow.queues.queueId` | EQUALS, NOT_EQUALS, IN, NIN |
| `contact.channelId` | IN, NIN, EQUALS, NOT_EQUALS |
| `externalCase.channelType` | EQUALS, NOT_EQUALS, IN, NIN |

**Example - Search Cases by Date Range:**
```json
{
  "filter": {
    "type": "AND",
    "filters": [
      {"type": "EQUALS", "key": "deleted", "values": [false]},
      {"type": "GTE", "key": "createdTime", "values": [1704067200000]},
      {"type": "LTE", "key": "createdTime", "values": [1706745600000]}
    ]
  },
  "sorts": [{"key": "createdTime", "order": "DESC"}],
  "page": {"size": 100},
  "includeCount": true
}
```

---

## MESSAGE Filter Keys

| Key | Supported Types |
|-----|-----------------|
| `sourceType` | IN, NIN, EQUALS, NOT_EQUALS |
| `sourceId` | IN, NIN, EQUALS, NOT_EQUALS |
| `channelType` | IN, NIN, EQUALS, NOT_EQUALS |
| `content.text` | IN, SEARCH |
| `content.title` | IN, NIN, EQUALS, NOT_EQUALS, CONTAINS |
| `brandPost` | EQUALS, NOT_EQUALS |
| `deleted` | IN, NIN, EQUALS, NOT_EQUALS |
| `enrichments.sentiment` | IN, NIN, EQUALS, NOT_EQUALS, GT, GTE, LT, LTE |
| `workflow.customProperties` | IN, NIN, EQUALS, NOT_EQUALS |
| `postId` | IN, NIN, EQUALS, NOT_EQUALS |

**MESSAGE Time Filter (Required):**
```json
{
  "timeFilter": {
    "key": "channelCreatedTime",
    "since": "2024-01",
    "until": "2024-03"
  }
}
```

---

## PROFILE Filter Keys

| Key | Supported Types |
|-----|-----------------|
| `id` | IN, NIN, EQUALS, NOT_EQUALS, LT, LTE, GT, GTE |
| `channelType` | IN, NIN, CONTAINS |
| `channelId` | IN, NIN, CONTAINS |
| `contact.email` | IN, NIN, EQUALS, NOT_EQUALS |
| `contact.phoneNo` | IN, NIN, EQUALS, NOT_EQUALS |
| `createdTime` | LT, LTE, GT, GTE, EQUALS |
| `modifiedTime` | LT, LTE, GT, GTE, EQUALS |

---

# Reference Data

## Channel Types

`FACEBOOK`, `TWITTER`, `LINKEDIN`, `INSTAGRAM`, `YOUTUBE`, `TIKTOK`, `WORKFLOW`, `SINA_WEIBO`, `VK`, `GOOGLE_PLUS`

## Common Message Type Codes

**Twitter:** 1 (Timeline), 2 (Update), 3 (Sent DM), 5 (Received DM), 7 (Reply), 8 (Retweet)

**Facebook:** 14 (Comment), 15 (Post), 38 (Private Message), 97 (Reply)

**Instagram:** 36 (Post), 37 (Comment), 306 (Reply), 320 (Direct Message)

**LinkedIn:** 16 (Post), 69 (Company Post), 70 (Company Comment)

## Attachment Types

`PHOTO`, `VIDEO`, `LINK`, `AUDIO`, `PDF`, `DOCUMENT`

## Language Codes

| Language | Code |
|----------|------|
| English | `en` |
| Spanish | `es` |
| French | `fr` |
| German | `de` |
| Portuguese | `pt` |
| Chinese | `zh` |
| Arabic | `ar` |

---

# Project-Specific Field IDs

| Field | ID | Path |
|-------|-----|------|
| Brand | `5cc9a7cfe4b01904c8dfc908` | `workflow.customProperties` |
| Language | `5cc9a7d0e4b01904c8dfc965` | `workflow.customProperties` |
| Country | `_c_66fcd9757813fc0020abeda3` | `workflow.customProperties` |

---

# Rate Limits

| Limit | Value |
|-------|-------|
| Per second | 10 calls |
| Per hour | 1,000 calls |

When rate limit exceeded: 403 response with `"Developer Over Rate"` error message.

Use `scripts/resume_ingestion.py` to continue after rate limit errors.

---

# HTTP Status Codes

| Range | Meaning |
|-------|---------|
| 2xx | Success |
| 4xx | Client error (bad request, auth, rate limit) |
| 5xx | Sprinklr server error |

## Common Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | - |
| 400 | Bad request / invalid payload | Check request body |
| 401 | Invalid/expired token | Refresh token or re-authenticate |
| 403 | Rate limit (`"Developer Over Rate"`) or insufficient permissions | Wait 1 hour or check permissions |
| 404 | Resource not found | Verify ID/case number exists |
| 429 | Rate limit exceeded | Wait and retry with backoff |
| 500 | Server error | Retry later |

---

# Currently Implemented

In `src/sprinklr_client.py`:

| Method | Endpoint | Function |
|--------|----------|----------|
| GET | `/api/v2/case/{caseId}` | `get_case()` |
| GET | `/api/v2/case/case-numbers` | `get_case_by_number()` |
| GET | `/api/v2/case/associated-messages` | `get_case_associated_message_ids()` |
| POST | `/api/v2/message/bulk-fetch` | `get_messages_bulk()` |
| GET | `/api/v2/message/byMessageId` | `get_message_by_id()` |
| POST | `/api/v1/case/search` | `search_cases_v1()` |
| POST | `/api/v2/search/CASE` | `search_cases_v2()` |
