import openai
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from langchain_core.agents import AgentAction, AgentFinish
from typing import Dict, TypedDict, Annotated, Union, List
import operator
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
import asyncio
import time
import nest_asyncio

# Allow nested event loops
nest_asyncio.apply()

# --- Define the state structure ---
class State(TypedDict):
    input: str  # Resume text
    chat_history: List[AIMessage]
    agent_outcome: Union[str, None]  # This could hold structured results
    intermediate_steps: Annotated[List[tuple[AgentAction, str]], operator.add]
    recipient_email: str  # Ensure state["recipient_email"] is part of the state
    user_input: str  # User's input for customization


# --- EmailAgent Class ---
class EmailAgent:
    def __init__(self, email_user: str, app_password: str, openai_api_key: str):
        self.email_user = email_user
        self.app_password = app_password
        openai.api_key = openai_api_key

    async def send_email(self, state: State) -> None:
        try:
            print("Please provide any additional details or customization you'd like to include in the email: ")
            user_input = input("Enter any specific details (leave blank to proceed with a standard email): ")

            # Generate email content using OpenAI
            prompt = f"""
            Write a polite and professional email to an employee requesting the details of tasks for today. The email should:

            - Start with a warm greeting and an expression of goodwill (e.g., "I hope this email finds you well").
            - Clearly and concisely state the purpose of the email, which is to request the details of today's tasks.
            - Emphasize the importance of receiving timely updates to ensure the smooth progression of work and proper prioritization of tasks.
            - Express an openness to further discussion or clarification if required, offering assistance or additional context if necessary.
            - Maintain a formal and courteous tone throughout the email, avoiding casual language.
            - End the email with gratitude and a polite closing (e.g., "Looking forward to your response" or "Thank you for your guidance").
            - Keep the email within a professional length—concise but detailed enough to convey the message effectively.

            {user_input}
            """ if user_input else """
            Write a polite and professional email to an employee requesting the details of tasks for today. The email should:

            - Start with a warm greeting and an expression of goodwill (e.g., "I hope this email finds you well").
            - Clearly and concisely state the purpose of the email, which is to request the details of today's tasks.
            - Emphasize the importance of receiving timely updates to ensure the smooth progression of work and proper prioritization of tasks.
            - Express an openness to further discussion or clarification if required, offering assistance or additional context if necessary.
            - Maintain a formal and courteous tone throughout the email, avoiding casual language.
            - End the email with gratitude and a polite closing (e.g., "Looking forward to your response" or "Thank you for your guidance").
            - Keep the email within a professional length—concise but detailed enough to convey the message effectively.
            """

            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a professional email assistant."}, {"role": "user", "content": prompt}],
                max_tokens=1050,
                temperature=0.1
            )

            email_content = response.choices[0].message.content.strip()

            # Prepare the email
            msg = MIMEText(email_content, "plain")
            msg["Subject"] = "Request for Today's Task Details"
            msg["From"] = self.email_user
            msg["To"] = state["recipient_email"]

            # Send the email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email_user, self.app_password)
                server.sendmail(self.email_user, state["recipient_email"], msg.as_string())

            print(f"Email sent to {state['recipient_email']}.")
        except Exception as e:
            print(f"Error sending email: {e}")

    async def fetch_latest_response(self, state: State) -> State:
        try:
            # Setup IMAP connection and fetch emails
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.email_user, self.app_password)
            mail.select("inbox")
            _, data = mail.search(None, f'FROM "{state["recipient_email"]}"')
            email_ids = data[0].split()

            if not email_ids:
                print("No emails found. Re-triggering notification...")
                return state

            latest_email_id = email_ids[-1]
            _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extract email content
            email_content = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        email_content = part.get_payload(decode=True).decode()
                        break
            else:
                email_content = msg.get_payload(decode=True).decode()

            state["input"] = email_content  # Update state with the fetched email content
            print(f"Fetched email content: {email_content[:100]}...")  # Print a snippet for confirmation
            return state

        except Exception as e:
            print(f"Error fetching response: {e}")
            return state

    async def analyze_response_with_openai(self, response_text: str, state: State) -> State:
        prompt = f"""
            Analyze the following email response:

            "{response_text}"

            Your analysis should address the following points:

            1. **Content Clarity**: 
            - Is the response clear and easy to understand? 
            - Does it adequately address the purpose of the original email?

            2. **Completeness**: 
            - Does the email provide all the requested information? 
            - Are there any key details missing that should have been included?

            3. **Tone and Professionalism**: 
            - Is the tone of the email appropriate (e.g., professional, polite, and formal)?
            - Highlight any areas where the tone could be improved.

            4. **Actionable Outcomes**: 
            - Does the response clearly indicate the next steps, if any? 
            - Are the instructions or outcomes actionable?

            5. **Suggestions for Improvement**: 
            - Provide constructive feedback on how the response could be improved in terms of clarity, detail, or professionalism.

            Conclude your analysis with a summary of the overall quality of the email response.
        """

        try:
            analysis_response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
                max_tokens=1050,
                temperature=0.1
            )

            analysis_result = analysis_response.choices[0].message.content.strip()
            state["agent_outcome"] = analysis_result
            print(f"Analysis Result: {analysis_result[:100]}...")  # Print a snippet for confirmation
            return state

        except Exception as e:
            print(f"Error analyzing with OpenAI: {e}")
            return state


# --- Workflow Definition ---
workflow = StateGraph(State)

# Wrap the methods to bind to EmailAgent instance
async def send_email_node(state):
    email_agent = EmailAgent(
        email_user="b8860157@gmail.com",
        app_password="wymr aicj ybtq xtnj",
        openai_api_key="your-api-code"
    )
    await email_agent.send_email(state)

async def fetch_latest_response_node(state):
    email_agent = EmailAgent(
        email_user="b8860157@gmail.com",
        app_password="wymr aicj ybtq xtnj",
        openai_api_key="your-api-key"
    )
    return await email_agent.fetch_latest_response(state)

async def analyze_response_with_openai_node(state: State):
    email_agent = EmailAgent(
        email_user="b8860157@gmail.com",
        app_password="wymr aicj ybtq xtnj",
        openai_api_key="your-api-key"
    )
    response_text = state["input"]  # Assuming the email response is in the 'input' field
    return await email_agent.analyze_response_with_openai(response_text, state)

async def monitor_response(state: State) -> State:
    response_received = False
    for _ in range(3):  # 3 attempts with a 6-second interval
        time.sleep(6)
        state = await fetch_latest_response_node(state)
        if state["input"]:  # If response is received
            response_received = True
            break
    if not response_received:
        await send_email_node(state)  # Resend the email
        print("Retrying email...")
        time.sleep(18)  # Wait again for a response
        state = await fetch_latest_response_node(state)
        if state["input"]:
            print("Response received.")
        else:
            print("Escalating to Slack.")
    return state

# Add nodes to the workflow
workflow.add_node("send_email", send_email_node)
workflow.add_node("monitor_response", monitor_response)
workflow.add_node("fetch_latest_response", fetch_latest_response_node)
workflow.add_node("analyze_response_with_openai", analyze_response_with_openai_node)

# Connect nodes
workflow.add_edge("send_email", "monitor_response")
workflow.add_edge("monitor_response", "fetch_latest_response")
workflow.add_edge("fetch_latest_response", "analyze_response_with_openai")
workflow.add_edge("analyze_response_with_openai", END)

# Set the entry point for the workflow
workflow.set_entry_point("send_email")  # Explicitly set `send_email` as the entry point

# Compile the workflow
final = workflow.compile()

# --- Main Function ---
async def main():
    initial_input = {
        "input": "Initial email request state", 
        "chat_history": [],
        "agent_outcome": None,
        "intermediate_steps": [],
        "recipient_email": "balajimsd098@gmail.com",
        "user_input": ""
    }

    try:
        await final.ainvoke(initial_input)
    except Exception as e:
        print(f"Error executing workflow: {e}")

if __name__ == "__main__":
    asyncio.run(main())

