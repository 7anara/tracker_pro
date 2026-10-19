from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from tracker_pro.chain.tools import build_user_tools
from tracker_pro.config import settings


def run_agent(message: str, user_id: int, today: str) -> str:
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    tools = build_user_tools(user_id)
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are Tracker Pro, a personal assistant. Reply in the user's language when possible.
The user's local date is {today}, timezone is {timezone}. Resolve relative dates from that date.
Use tools for database reads and writes. Never ask for or accept another user's identity.
Before changing/deleting a task without an ID, call get_tasks and match by title. If no unique match exists, ask a clarifying question.
Do not save meal suggestions unless the user explicitly asks to save/create a plan. For healthy meal suggestions, provide balanced practical choices; if asked to save, use create_meal_plan.
Only claim changes that a tool confirms. Ask for missing required meal details when necessary."""),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key, temperature=0)
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True)
    result = executor.invoke({
        "input": message,
        "today": today,
        "timezone": settings.app_timezone,
    })

    output = result.get("output")

    print("Agent output type:", type(output).__name__)
    print("Agent output is empty:", not bool(output))

    return output



