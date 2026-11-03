import os.path
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes define what Jarvis is allowed to read and write
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/calendar'
]

class GoogleWorkspaceBridge:
    def __init__(self, credentials_path="credentials.json", token_path="token.json", lazy_auth=True):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
        self._gmail_service = None
        self._tasks_service = None
        self._calendar_service = None
        self._auth_initialized = False
        self._auth_lock = threading.Lock()
        
        # Load existing user token if previously authorized without network I/O
        if os.path.exists(token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception as e:
                print(f"[Workspace Bridge] Failed to load {token_path}: {e}")
                self.creds = None

        if not lazy_auth:
            self._ensure_authenticated()
        else:
            # Asynchronously validate and refresh credentials in background
            threading.Thread(target=self._ensure_authenticated, daemon=True, name="WorkspaceAuthThread").start()

    def _ensure_authenticated(self):
        """Thread-safe lazy initialization and token refresh."""
        with self._auth_lock:
            if self._auth_initialized:
                return
            self._auth_initialized = True

            # If token is invalid or expired, attempt refresh
            if self.creds and not self.creds.valid:
                if self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                        with open(self.token_path, 'w') as token:
                            token.write(self.creds.to_json())
                    except Exception as e:
                        print(f"[Workspace Bridge] Token refresh failed: {e}. Re-authorization required.")
                        self.creds = None

            if self.creds and self.creds.valid:
                try:
                    self._gmail_service = build('gmail', 'v1', credentials=self.creds)
                    self._tasks_service = build('tasks', 'v1', credentials=self.creds)
                    self._calendar_service = build('calendar', 'v3', credentials=self.creds)
                    print("[Workspace Bridge] Gmail, Tasks & Calendar APIs linked successfully.")
                except Exception as e:
                    print(f"[Workspace Bridge] Failed to initialize Google API clients: {e}")
            else:
                print("[Workspace Bridge] Warning: Workspace offline or credentials unverified. Core operations will continue.")

    @property
    def gmail_service(self):
        if not self._auth_initialized:
            self._ensure_authenticated()
        return self._gmail_service

    @gmail_service.setter
    def gmail_service(self, val):
        self._gmail_service = val

    @property
    def tasks_service(self):
        if not self._auth_initialized:
            self._ensure_authenticated()
        return self._tasks_service

    @tasks_service.setter
    def tasks_service(self, val):
        self._tasks_service = val

    @property
    def calendar_service(self):
        if not self._auth_initialized:
            self._ensure_authenticated()
        return self._calendar_service

    @calendar_service.setter
    def calendar_service(self, val):
        self._calendar_service = val
        
    def get_unread_emails(self, max_results=5):
        """Fetches latest unread emails from inbox."""
        if not self.gmail_service:
            return "Google Workspace Gmail service is currently offline."
        try:
            results = self.gmail_service.users().messages().list(
                userId='me', q='is:unread', maxResults=max_results
            ).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return "No unread emails found."
                
            summary_list = []
            for msg in messages:
                detail = self.gmail_service.users().messages().get(userId='me', id=msg['id']).execute()
                headers = detail['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                snippet = detail.get('snippet', '')
                summary_list.append(f"From: {sender} | Subject: {subject}\nSnippet: {snippet}")
                
            return "\n---\n".join(summary_list)
        except Exception as e:
            return f"Failed to retrieve emails: {e}"

    def create_task(self, title: str, notes: str = None):
        """Creates a Google Task that syncs across PC and Mobile."""
        if not self.tasks_service:
            return "Google Tasks service is currently offline."
        try:
            task_body = {'title': title}
            if notes:
                task_body['notes'] = notes
                
            result = self.tasks_service.tasks().insert(tasklist='@default', body=task_body).execute()
            return f"Task scheduled: '{result.get('title')}'"
        except Exception as e:
            return f"Failed to create task: {e}"

    def create_calendar_event(self, summary: str, start_iso: str, end_iso: str):
        """Creates a precise Calendar event with an aggressive push notification."""
        if not self.calendar_service:
            return "Google Calendar service is currently offline."
        try:
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_iso,
                    'timeZone': 'Asia/Kolkata', # Defaulting to your local temporal zone
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': 'Asia/Kolkata',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 0} # Buzz the phone at exact start time
                    ],
                },
            }

            event_result = self.calendar_service.events().insert(
                calendarId='primary', body=event).execute()
            return f"Alarm set: '{event_result.get('summary')}' scheduled successfully."
        except Exception as e:
            return f"Failed to set precise alarm: {e}"

    def get_upcoming_events(self):
        """Fetches all events happening in the next 24 hours."""
        if not self.calendar_service:
            return []
        from datetime import datetime, timedelta
        import pytz

        try:
            now = datetime.now(pytz.timezone('Asia/Kolkata'))
            time_min = now.isoformat()
            time_max = (now + timedelta(days=1)).isoformat()

            events_result = self.calendar_service.events().list(
                calendarId='primary', timeMin=time_min, timeMax=time_max,
                singleEvents=True, orderBy='startTime').execute()
            
            return events_result.get('items', [])
        except Exception as e:
            print(f"[Workspace Bridge] Calendar fetch error: {e}")
            return []