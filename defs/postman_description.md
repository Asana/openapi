# Asana API

Welcome to the Asana API!

This is the interface for interacting with the [Asana Platform](https://developers.asana.com).

## How to Use This Postman Collection

### 1. Fork the Collection

[Create a fork in your Postman workspace](https://god.gw.postman.com/run-collection/37831743-a37a0580-d957-4a08-8fe0-c5c905679037?action=collection%2Ffork&source=rip_markdown&collection-url=entityId%3D37831743-a37a0580-d957-4a08-8fe0-c5c905679037%26entityType%3Dcollection%26workspaceId%3Df59a5f48-be65-4e04-abcd-c56edd9bdb9a) and enable **Watch original collection** to receive notifications when the collection is updated.

### 2. Configure Variables

Navigate to the **Variables** tab in the collection root and set the required variables.

### 3. Authenticate

Navigate to the **Authorization** tab in the collection root and choose your authentication method:

#### Option A: OAuth 2.0

Best for testing endpoints specific to your app. Postman's built-in OAuth 2.0 support lets you get an access token in seconds.

1. Copy your **Client ID** and **Client Secret** from the [Asana Developer Console](https://app.asana.com/0/my-apps)
2. Paste them into the `oauthAppId` and `oauthSecret` variables in Postman
3. Set `oauthScopes` to your app's required scopes (space-separated)
4. Click **Get New Access Token** at the bottom
5. You're ready to make requests!

#### Option B: Personal Access Token

The fastest way to get started if you don't need OAuth.

1. Select **Bearer Token** from the **Auth Type** dropdown
2. In the **Token** field, enter: `{{bearerToken}}`
3. Set the `bearerToken` variable to your [Personal Access Token](https://app.asana.com/0/my-apps)

### 4. Start Making Requests

You're all set! Begin exploring the API endpoints.

### 5. Keep Your Fork Updated

When you receive a notification about updates:

1. Click on **Asana** (your collection name)
2. Click the **three dots** menu and select **Pull changes**
3. Review and resolve any conflicts in the diff checker
4. Confirm to update your collection

## Learn More

This collection helps you test endpoints quickly. For comprehensive documentation, tutorials, and guides, visit the [Asana Developers portal](https://developers.asana.com/docs/overview).

### Helpful Resources

- [API Reference](https://developers.asana.com/reference/rest-api-reference)
- [Getting Started Guide](https://developers.asana.com/docs/quick-start)
- [Authentication Documentation](https://developers.asana.com/docs/authentication)
- [Developer Community](https://forum.asana.com/c/forum-en/api/24)