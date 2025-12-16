# GitHub OAuth Setup Guide

This guide walks you through setting up GitHub OAuth for the ContriVerse platform.

## Step 1: Register GitHub OAuth App

1. Go to **GitHub Settings** → **Developer settings** → **OAuth Apps**
   - Direct link: https://github.com/settings/developers

2. Click **"New OAuth App"**

3. Fill in the application details:
   - **Application name**: `ContriVerse` (or your preferred name)
   - **Homepage URL**: `http://localhost:8000` (for development)
   - **Application description**: `Open source contribution tracking platform` (optional)
   - **Authorization callback URL**: `http://localhost:8000/api/v1/auth/github/callback`

4. Click **"Register application"**

## Step 2: Get OAuth Credentials

After registration, you'll see your OAuth app details:

1. Copy the **Client ID**
2. Click **"Generate a new client secret"**
3. Copy the **Client Secret** (you won't be able to see it again!)

## Step 3: Configure Application

1. Open your `.env` file (or create one from `.env.example`):
   ```bash
   cp .env.example .env
   ```

2. Update the GitHub OAuth credentials:
   ```bash
   GITHUB_CLIENT_ID=your_client_id_here
   GITHUB_CLIENT_SECRET=your_client_secret_here
   GITHUB_REDIRECT_URI=http://localhost:8000/api/v1/auth/github/callback
   ```

3. Ensure `SECRET_KEY` is set (already generated during setup):
   ```bash
   SECRET_KEY=your_generated_secret_key
   ```

## Step 4: Required Scopes

The application requests the following minimal scopes:
- `read:user` - Read user profile information
- `user:email` - Read user email addresses

These are automatically requested during the OAuth flow.

## Step 5: Test OAuth Flow

1. Start the application:
   ```bash
   make docker-up
   ```

2. Visit the login endpoint:
   ```
   http://localhost:8000/api/v1/auth/github/login
   ```

3. You'll be redirected to GitHub to authorize the application

4. After authorization, you'll be redirected back with access and refresh tokens

5. Test the `/auth/me` endpoint with your access token:
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
        http://localhost:8000/api/v1/auth/me
   ```

## OAuth Flow Diagram

```
User → /auth/github/login
  ↓
GitHub Authorization Page
  ↓
User Authorizes
  ↓
GitHub → /auth/github/callback?code=...&state=...
  ↓
Backend exchanges code for GitHub token
  ↓
Backend fetches user profile
  ↓
Backend creates/updates user
  ↓
Backend returns JWT tokens
  ↓
User authenticated ✓
```

## Security Features

- **CSRF Protection**: OAuth state parameter validation
- **Token Rotation**: Refresh tokens are rotated on each refresh
- **Secure Storage**: Refresh tokens are hashed in database
- **Token Expiry**: Access tokens expire in 30 minutes, refresh tokens in 7 days
- **Strict Validation**: Redirect URI validation prevents token theft

## Production Setup

For production deployment:

1. Update the **Homepage URL** to your production domain
2. Update the **Authorization callback URL** to your production callback
3. Update `.env` with production URLs:
   ```bash
   GITHUB_REDIRECT_URI=https://yourdomain.com/api/v1/auth/github/callback
   ```

## Troubleshooting

### "Invalid OAuth state parameter"
- The state parameter expired (10 minutes)
- Try logging in again

### "Failed to exchange code for token"
- Check that `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are correct
- Verify the authorization callback URL matches exactly

### "User not found"
- The JWT token is invalid or expired
- Try logging in again

### "Your account has been banned"
- Contact platform administrators

## API Endpoints

- `GET /api/v1/auth/github/login` - Initiate OAuth flow
- `GET /api/v1/auth/github/callback` - OAuth callback (automatic)
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout (invalidate refresh token)
- `GET /api/v1/auth/me` - Get current user info (requires auth)

## Next Steps

After authentication is working:
1. Implement protected API endpoints
2. Add role-based access control
3. Implement project and repository management
4. Build the contribution tracking system
