 

## POST Read Message (Bulk)

You can use this API to fetch messages in bulk that are associated with the respective message Ids.

### API Endpoint

https://api3.sprinklr.com`/{env}/`api/v2/message/bulk-fetch

### Headers

The following set of HTTP header fields provide required information about the request or response, or about the object sent in the message body. Both request headers and response headers can be controlled using these endpoints.

| Key | Value | Description |
| --- | --- | --- |
| accept | `application/json` | Specifies the content types that are valid in the response message. If the server cannot respond with the requested content type, the 406 Not Acceptable HTTP status message is returned. |
| Authorization | `Bearer {token}` | Credential used by an application to access an API. |
| Key | `api-key` | The API key acts as both a unique identifier and a secret token for authentication to a set of access rights. |
| Content-Type | application/json | Request format should be JSON as the endpoint expects a JSON body. |

### Request Parameters

| Parameter | Required/Optional | Description | Type |
| --- | --- | --- | --- |
| messageId | Required | The message Ids of the messages you want to fetch | List of strings |

**Dev Notes:** `messageId`\= **sourceType** (ACCOUNT, PERSISTENT\_SEARCH, LISTENING) + “\_”+ **sourceId** + “\_” + **channelCreatedTime** + “\_” + “**[channelType](moz-extension://520d5046-4a59-491e-89ae-ce3674380e2a/channels-v1)**” + “\_” + ” **[messageType](moz-extension://520d5046-4a59-491e-89ae-ce3674380e2a/message-v1)**“ +”\_” + **channelMessageId**

## Example
curl -X POST \
  https://api3.sprinklr.com/{env}/api/v2/message/bulk-fetch \
  -H 'Authorization: Bearer {Enter your Access Token}' \
  -H 'Key: {Enter your API KEY}' \
  -H 'accept: application/json' 
-d '[
   "VOICE_66076376_1731588218296_SPRINKLR_VOICE_325_000001932ab35db8e4b042fc69f4425d",
	"VOICE_66076376_1731588218296_SPRINKLR_VOICE_325_000001932ab35db8e4b042fc69f4476e"
    ]



## Sample - Response
{
    "data": [
        {
            "sourceType": "VOICE",
            "sourceId": 66076376,
            "content": {
                "attachment": {
                    "commands": [
                        {
                            "from": "+12025391107",
                            "type": "INCOMING_CALL"
                        }
                    ],
                    "type": "VOICE"
                },
                "isRichText": false
            },
            "channelMessageId": "000001932ab35db8e4b042fc69f4425d",
            "channelType": "SPRINKLR_VOICE",
            "accountType": "SPRINKLR_VOICE",
            "channelCreatedTime": 1731588218296,
            "senderProfile": {
                "name": "+12025391107",
                "channelType": "SPRINKLR_VOICE",
                "channelId": "+12025391107",
                "followers": 0,
                "following": 0,
                "username": "+12025391107",
                "unSubscribed": false,
                "deleted": false,
                "snCreatedTime": 0,
                "snModifiedTime": 1731590506410,
                "statusCount": 0,
                "accountSpecificInfos": [
                    {
                        "accountId": 600053936
                    },
                    {
                        "accountId": 66076376
                    }
                ],
                "additional": {
                    "PHONE_NUMBER_LINE": [
                        "LANDLINE"
                    ],
                    "PHONE_NO": [
                        "2025391107"
                    ],
                    "COUNTRY_CODE": [
                        "+1"
                    ]
                }
            },
            "receiverProfile": {
                "name": "Vishesh app_DND_New",
                "channelType": "SPRINKLR_VOICE",
                "channelId": "+15077044489",
                "followers": 0,
                "following": 0,
                "username": "Vishesh app_DND_New",
                "unSubscribed": false,
                "deleted": false,
                "snCreatedTime": 0,
                "snModifiedTime": 1731582171907,
                "statusCount": 0,
                "accountSpecificInfos": [],
                "additional": {}
            },
            "messageId": "VOICE_66076376_1731588218296_SPRINKLR_VOICE_325_000001932ab35db8e4b042fc69f4425d",
            "brandPost": false,
            "createdTime": 1731588218337,
            "modifiedTime": 1731588218337,
            "textEntities": {},
            "insights": {},
            "workflow": {},
            "enrichments": {
                "sentiment": 0,
                "flaggedWords": {
                    "allFlaggedWords": [],
                    "imageFlaggedWords": [],
                    "messageFlaggedWords": [],
                    "videoFlaggedWords": []
                }
            },
            "conversationId": "000001932ab35afae4b042fc69f4425b",
            "autoImported": false,
            "autoResponse": false,
            "associatedCaseNumber": 5313675
        }
    ],
    "errors": []
}           


### Response Parameters

| Parameters | Sub-Parameters | Description | Type |
| --- | --- | --- | --- |
| draftId |  | The draft Id of the message | Integer |
| sourceType |  | Message SourceType = {ACCOUNT, PERSISTENT\_SEARCH, LISTENING} | String |
| sourceId |  | accountId or PS Id | String |
| content |  | Object containing message details | Object |
|  | title | The title of the message (if any) | String |
|  | text | The text of the message | String |
|  | attachment | Refers to the object containing the attachments present on the message (if any)
Refer to the table below for the attachment object details

 | Object |
|  | isRichText | If true, the context is a rich text format | Boolean |
| channelMessageId |  | A unique identifier for the channel | String |
| channelType |  | The [type of channel](moz-extension://520d5046-4a59-491e-89ae-ce3674380e2a/channels-v1) where the message exists | String |
| accountType |  | The type of account where the message exists | String |
| channelCreatedTime |  | Time the message was created in native | Epoch |
| senderProfile |  | Refers to the object containing the sender profile details

Refer to the table below for senderProfile object details

 | Array |
| receiverProfile |  | Refers to the object containing the receiver profile details

Refer to the table below for receiverProfile object details

 | Array |
| mentionedProfiles |  | Array that stores information about the mentionedProfiles

Refer to the table below for mentionedProfiles array details

 | Array |
| language |  | The language used in the native channel

**Example**: “en” for English

Refer to the table below for commonly used language codes

 | String |
| messageId |  | Refers to the unique identifier for the message sent by the sender | String |
| postId |  | Post Id of the message | String |
| brandPost |  | If true, the message has been sent by the brand | Boolean |
| createdTime |  | Time at which the message was created | Epoch |
| modifiedTime |  | The time at which the message was modified | Epoch |
| textEntities |  | Provides metadata and any additional details related to a message | Object |
| Insights |  | Refers to the object containing the message insights such as:

POST\_REACH\_COUNT, POST\_COMMENT\_COUNT

 | Object |
| workflow |  | workflow properties related to the message | Object |
|  | modifiedTime | The time at which the message was modified | Epoch |
|  | customProperties | Custom properties related to the message | Object |
|  | queues | The queue in which the message has been added. Refer to the table below for the queue array details | Array |
|  | spaceWorkflows | SpaceWorkflows are the workflow properties that are specific to a space (Earlier known as client). This has attributes like client queues and client custom fields. | Object |
|  | campaignId | The campaign under which the message is published | String |
| enrichments |  | List of enrichment metadata derived for a user

Refer to the table below for enrichments object description

 | Object |
| conversationMessageId |  | Refers to the unique identifier for the conversation | String |
| parentMessageId |  | Unique universal Id of the message | String |
| autoImported |  | If True, then

the message was not published by sprinklr. It has been imported

 | Boolean |
| autoResponse |  | If true, then

the message was auto published via bot or via rule

 | Boolean |
| apiStatus |  | Describes the status of the API | String |

### attachment Object Description Table

| Parameters | Description | Type |
| --- | --- | --- |
| url | Refers to the URL of the attachment | String |
| title | Refers to the title of the attachment | String |
| previewUrl | Refers to the preview Url link of the attachment | String |
| type | Refers to the type of the attachment such as IMAGE, VIDEO, AUDIO, DOC | String |

### Commonly Used Language Codes

| Language | Code |
| --- | --- |
| English (US) | en |
| Deutsch (German) | d |
| Español (Spanish) | es |
| Français (France) | fr |
| Italiano (Italian) | it |
| Português (Brasil) | pt |
| Русский (Russian) | ru |
| (Arabic) | ar |
| (Chinese) | zh |

### Sender Profile/Receiver/Mentioned Profile Parameter Description Table

| Parameters | Description | Type |
| --- | --- | --- |
| name | Refers to the name associated with the user profile | String |
| channelType | The type of channel where the profile exists | String |
| channelId | Channel Id associated with the profile on the native | String |
| avatarUrl | Refers to the avatar Url associated with the profile picture | String |
| profileImageUrl | Refers to the display picture Url of the profile as available on the native channel | String |
| permalink | Profile URL on the native channel | URL |
| followers | Number of followers for the respective profile | Integer |
| following | Number of people the user is following | Integer |
| username | Refers to the username of the user as mentioned on the native channel | String |
| unSubscribed | If true, the profile has been unsubscribed | Boolean |
| deleted | If true, the profile is deleted on the native | Boolean |
| snCreatedTime | Refers to the profile creation time on native | Epoch |
| snModifiedTime | Refers to the profile modified time on native | Epoch |
| statusCount | The number of statuses published from the profile | Integer |
| accountSpecificInfos | Refers to the object containing the meta data associated with the account
Refer to the table below for accountSpecificInfos object details

 | Object |
| additional | Refers to the object containing the additional details associated with the profile | Object |

## queues Array Description Table

| Parameters | Description | Type |
| --- | --- | --- |
| queueId | Refers to the unique identifier for the queue where the message has been added | Integer |
| assignmentTime | Refers to the time at which the message was added to the given queue | Epoch (milliseconds) |

## enrichments Object Description Table

| Parameters | Sub-Parameter | Description | Type |
| --- | --- | --- | --- |
| sentiment |  | Refers to the sentiment of the message, i.e., positive, negative, or neutral | Integer |
| flaggedWords |  | Refers to the object containing the flagged words | Object |
|  | allFlaggedWords | Refers to the list of all the flagged words | List \[String\] |
|  | imageFlaggedWords | Refers to the list of flagged words present in the images | List \[String\] |
|  | messageFlaggedWords | Refers to the list of flagged words present in the message | List \[String\] |
|  | videoFlaggedWords | Refers to the list of flagged words present in the video | List \[String\] |

## accountSpecificInfos Object Description Table

| Parameters | Description | Type |
| --- | --- | --- |
| accountId | Refers to the unique identifier for the brand's social account existing within Sprinklr | Integer |
| lastBrandEngagedTime | Refers to the time at which the brand last replied on the message | Epoch (milliseconds) |
| lastFanEngagedTime | Refers to the time at which the customer last replied on the message | Epoch (milliseconds) |
| activeUser | If true, the user has a active social account | Boolean |

[](moz-extension://520d5046-4a59-491e-89ae-ce3674380e2a/read-messages-bulk)

[Back to top](moz-extension://520d5046-4a59-491e-89ae-ce3674380e2a/read-messages-bulk)