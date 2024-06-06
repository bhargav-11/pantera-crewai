from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path
import base64

SCOPES = ['https://www.googleapis.com/auth/calendar']

def save_credentials(creds):
    """Save Google OAuth credentials to a pickle file."""
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

def load_credentials():
    """Load Google OAuth credentials from a pickle file, if it exists."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    return creds

def authenticate_google_calendar(scopes):
    """Authenticate and obtain credentials for Google Calendar access."""
    creds = load_credentials()
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            creds = flow.run_local_server(port=0)
        save_credentials(creds)
    return creds

def encode_credentials_to_base64():
    """Encode the credentials stored in the pickle file to base64 and print it."""
    # Ensure we have valid credentials, and they are saved
    creds = authenticate_google_calendar(SCOPES)
    
    # Load and encode the credentials
    with open('token.pickle', 'rb') as token_file:
        token_data = token_file.read()
    encoded_token = base64.b64encode(token_data).decode('utf-8')
    print(encoded_token)

# Encode and print the credentials
encode_credentials_to_base64()
