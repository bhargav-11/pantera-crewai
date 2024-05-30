from flask import Flask, request, jsonify
import os

# Your existing imports (minus the infinite loop and input handling)
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from tools import GoogleCalendarTool
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(".env")

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
# Initialize Flask app
app = Flask(__name__)

# Include the custom GoogleCalendarTool
calendar_tool = GoogleCalendarTool()

# Agent focused on conversation and information
conversational_agent = Agent(
    role='Conversation expert',
    goal="Support the user's queries with accurate information.",
    backstory="""You are an expert conversationalist with a knack for providing insightful responses. 
                consider provided chat history for previous conversations.
                When it comes to booking meetings, you need to call 'Events/Meeting Organizer' agent.""",
    verbose=True,
    allow_delegation=True,  # Allow this agent to delegate tasks
    llm=ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0),
)

# New agent dedicated to handling calendar events
calendar_agent = Agent(
    role='Events/Meeting Organizer',
    goal="Manage and book calendar events/meetings as requested",
    backstory="""Equipped with the calendar_tool, you're the go-to agent for meeting booking. Today's date is {} and day is {}
              You handle all things related to calendar management.
              calendar_tool takes title, start_time, duration, attendees as arguments.
              start_time is in '2024-MM-DDThh:mm:00+-HH:MM' format. Based on provided city of the user, you need to get the timezone and construct start time in '2024-MM-DDThh:mm:00+-HH:MM' format.
              Duration is in number which represents number of minutes. The default meeting duration is 30 min.
              If user rejects the slot suggested, then present them with this link 'https://calendar.google.com/calendar/u/2/embed?src=hernan@panteragpt.com' to have a view of available slots in calendar and book a meeting """.format(str(datetime.now().isoformat()), str(datetime.now().strftime("%A"))),
    verbose=True,
    allow_delegation=True,  # This agent does not delegate tasks
    tools=[calendar_tool],  # Utilizes the GoogleCalendarTool for booking events
)
global chat_history
chat_history = []


@app.route('/api/chat', methods=['POST'])
def handle_query():

    print(request.json)

    data = request.json
    user_query = data.get('query')

    if not user_query:
        return jsonify({"error": "No query provided"}), 400
    
    if user_query in ['start', 'Start']:
        chat_history.clear()
        return

    # Format chat history as a string
    chat_history_str = "\n".join(["Human: {}\nAI: {}".format(entry["Human"], entry["AI"]) for entry in chat_history[-4:]])

    # Create tasks for your agents
    task1 = Task(
      description="""You need to respond to a user query with the most accurate information possible.
      chat_history: {}

      user query: {}
      """.format(chat_history_str, user_query),
      expected_output="response to user query or meeting booked",
      agent=conversational_agent,

    )

    # Instantiate your crew with a sequential process
    crew = Crew(
      agents=[conversational_agent, calendar_agent],
      tasks=[task1],
      verbose=2, # You can set it to 1 or 2 for different logging levels
    )

    # Get your crew to work!
    result = crew.kickoff()

    chat_history.append({"Human": user_query, "AI": result})

    return jsonify({"response": result})

if __name__ == '__main__':
    app.run(debug=True)