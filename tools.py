from crewai_tools import BaseTool
import pickle
import os.path
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.cloud import storage
import os
import base64
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv(".env")

# os.environ["TOKEN"] = "gASVwQMAAAAAAACMGWdvb2dsZS5vYXV0aDIuY3JlZGVudGlhbHOUjAtDcmVkZW50aWFsc5STlCmBlH2UKIwFdG9rZW6UjNp5YTI5LmEwQWQ1Mk4zLVo1LU4wdWtYU3lRMnpDcGF5d3U3NmdUelFwR3VWNWNoVmp1S1hjc3FIcnVEV19CdEt2U2pyZENiWFlVU1paZ0V1MzNKQ0tRSkljdmZjRWRVeV9ZYkhkd1JNYVE3MnJvMnBnMWJqb3Q2UGZUNmtwOUxsRjVhY1B3eU9Tc0ZOYlJoOXEzbC15bHhieE8wLTZiUW42M2RuWmpUdFdFdmVhQ2dZS0FTOFNBUkVTRlFIR1gyTWlTSXAyV1ZSQmtRak5nbzdqcGExRGZnMDE3MZSMBmV4cGlyeZSMCGRhdGV0aW1llIwIZGF0ZXRpbWWUk5RDCgfoAx4HEigORTSUhZRSlIwRX3F1b3RhX3Byb2plY3RfaWSUTowPX3RydXN0X2JvdW5kYXJ5lE6MEF91bml2ZXJzZV9kb21haW6UjA5nb29nbGVhcGlzLmNvbZSMGV91c2Vfbm9uX2Jsb2NraW5nX3JlZnJlc2iUiYwHX3Njb3Blc5RdlIwoaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vYXV0aC9jYWxlbmRhcpRhjA9fZGVmYXVsdF9zY29wZXOUTowOX3JlZnJlc2hfdG9rZW6UjGcxLy8wZ044TUNjT2ZweUxqQ2dZSUFSQUFHQkFTTndGLUw5SXJDdHdmbWJ1NXd3RFZ3cXFORmVqWXVRbl9TbDJkb2Z6WU95MjZSUWk0Z3AteVN2Njg3YjdWM1BHejRrMl9QVTMxbVNRlIwJX2lkX3Rva2VulE6MD19ncmFudGVkX3Njb3Blc5RdlIwoaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vYXV0aC9jYWxlbmRhcpRhjApfdG9rZW5fdXJplIwjaHR0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW6UjApfY2xpZW50X2lklIxIOTUyOTk4MDAwOTM2LW0xbWpqb3BidjBqZHYyNHZzNDFobmdlZDUxY3RqNWtiLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tlIwOX2NsaWVudF9zZWNyZXSUjCNHT0NTUFgtR19QTHpYVDBhbDZWRFZtTjVfZllHeG1KWXpESpSMC19yYXB0X3Rva2VulE6MFl9lbmFibGVfcmVhdXRoX3JlZnJlc2iUiYwIX2FjY291bnSUjACUdWIu"

TOKEN = os.environ.get('TOKEN')
# Function to load token from environment variable
def load_token():
    encoded_token = os.environ.get('TOKEN')
    if encoded_token:
        token_data = base64.b64decode(encoded_token.encode('utf-8'))
        return pickle.loads(token_data)
    return None

creds = load_token()

class GoogleCalendarTool(BaseTool):
    name: str = "GoogleCalendarEventBooking"
    description: str = """
            Tool to book events on Google Calendar.
            Takes meeting title, start_time, duration and attendees as input.
            attendees is a list of strings. title is string and duration is integer.
            attendees are optional.
        """

    def _run(self, title, start_time, duration, attendees=[]):
        # Convert start_time to datetime object and calculate end_time
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration)
        end_time = end_dt.isoformat()

        print(start_dt)
        print(end_dt)
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Step 1: Query for existing events
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat()
        ).execute()

        events = events_result.get('items', [])
        events = [event for event in events if event['eventType'] != 'workingLocation']
        
        # Step 2: Check for overlaps
        if events:  # If there are any events in the time range, consider it as overlap
            # Step 2: Query for all events on the day to find next available slot
            day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_events_result = service.events().list(
                calendarId='primary',
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            day_events = day_events_result.get('items', [])
            day_events = [event for event in day_events if event['eventType'] != 'workingLocation']

            # Function to find next available slot
            def find_next_available_slot(events, start_time, duration):
                print(events)
                current_time = start_time
                for event in events:
                    event_start = datetime.fromisoformat(event['start'].get('dateTime'))
                    event_end = datetime.fromisoformat(event['end'].get('dateTime'))
                    if current_time + timedelta(minutes=duration) <= event_start:
                        return current_time
                    current_time = max(current_time, event_end)
                if current_time < datetime.fromisoformat(day_end.isoformat()):
                    return current_time
                return None

            next_available_start = find_next_available_slot(day_events, datetime.fromisoformat(start_dt.isoformat()), duration)
            if next_available_start:
                next_available_end = next_available_start + timedelta(minutes=duration)
                return f"The slot is occupied. The next available slot is from {next_available_start} to {next_available_end}. Do you wanna book this slot ?"
            else:
                return "The slot is occupied and no other slots available for mentioned date."
        else:
            print("No events in the time range.")
            # Step 3: Create the event if no overlap
            event = {
                'summary': title,
                'start': {'dateTime': start_time, 'timeZone': 'America/New_York'},
                'end': {'dateTime': end_time, 'timeZone': 'America/New_York'},
                'attendees': [{'email': attendee} for attendee in attendees],
                'reminders': {
                    'useDefault': False,
                    'overrides': [{'method': 'email', 'minutes': 24 * 60}, {'method': 'popup', 'minutes': 10}],
                },
            }
            try:
                created_event = service.events().insert(calendarId='primary', body=event, sendUpdates='all').execute()
                return 'Event created: {}'.format(created_event.get('htmlLink'))
            except Exception as e:
                return f"An error occurred: {e}"


# class GetCurrentDateAndDay(BaseTool):
#     name: str = "GetCurrentDateAndDay"
#     description: str = """
#             Tool to get today's date and day
#         """

#     def _run(self):
#         return datetime.now().isoformat(), datetime.now().strftime("%A")