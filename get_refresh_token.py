# get_refresh_token.py
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

print("🚀 Starting OAuth flow...")
print("Browser will open. Sign in with jobs@hiringcircle.us or admin@hiringcircle.us")

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

print("\n" + "="*70)
print("✅ SUCCESS! Add these to Railway Environment Variables:")
print("="*70)
print(f'\nGMAIL_REFRESH_TOKEN={creds.refresh_token}')
print(f'\nGMAIL_CLIENT_ID={creds.client_id}')
print(f'\nGMAIL_CLIENT_SECRET={creds.client_secret}')
print("\n" + "="*70)
print("⚠️  IMPORTANT: Keep these values secret! Never commit to GitHub.")
print("="*70)