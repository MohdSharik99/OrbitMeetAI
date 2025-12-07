from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

# transcript = """
# [00:00:02] John Doe
# Hi everyone, thanks for joining today's sync. We'll go over the project updates and blockers.
#
# [00:00:10] Sarah Smith
# Thanks John. I’ll start with my update. The API integration for the payment service is about 80% complete.
# I expect to finish the remaining tasks by Thursday.
#
# [00:00:25] John Doe
# Great. Any blockers?
#
# [00:00:27] Sarah Smith
# Yes, I’m waiting for access to the staging environment. I've already raised a ticket but haven't received approval yet.
#
# [00:00:40] Michael Lee
# I can help with that. I’ll follow up with DevOps and get the access approved today.
#
# [00:00:48] John Doe
# Perfect. Michael, your updates?
#
# [00:00:50] Michael Lee
# Sure. The UI redesign for the dashboard is complete. I’ve pushed it to the feature branch.
# Only pending item is final QA review scheduled for tomorrow.
#
# [00:01:05] John Doe
# Good progress. Before we wrap up, any announcements or concerns?
#
# [00:01:12] Sarah Smith
# None from my side.
#
# [00:01:14] Michael Lee
# All good here.
#
# [00:01:17] John Doe
# Alright, thanks everyone. We'll meet again next Monday. Have a great day!
# """


# --------------------------------------------------------------------------------------------
# LLM
# --------------------------------------------------------------------------------------------

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.3,
    api_key=api_key
)


# --------------------------------------------------------------------------------------------
# Summary analysis
# # --------------------------------------------------------------------------------------------

# # Usage
# summary_agent = MeetingSummaryAnalyst(model=llm, tools=[])
#
# # Get validated Pydantic object
# summary = asyncio.run(summary_agent.agenerate_summary(transcript))
#
# # This will display as a Pydantic object
# print(summary)

# # --------------------------------------------------------------------------------------------
# # Participant Analyst Agent
# # --------------------------------------------------------------------------------------------
# #
# participant_agent = ParticipantSummaryAnalyst(model=llm, tools= [])
#
# p_result = asyncio.run(participant_agent.aparticipant_analysis(input_transcript=transcript))
#
#
# # print(p_result)
#
# def pretty_print_user_summaries(user_summaries):
#     for idx, item in enumerate(user_summaries, start=1):
#         ps = item  # UserSummary object
#         print(f"{idx}. {ps.participant_name}")
#
#         print("   - Key Updates:")
#         if ps.key_updates:
#             for k in ps.key_updates:
#                 print(f"       • {k}")
#         else:
#             print("       (none)")
#
#         print("   - Roadblocks:")
#         if ps.roadblocks:
#             for r in ps.roadblocks:
#                 print(f"       • {r}")
#         else:
#             print("       (none)")
#
#         print("   - Actionable:")
#         if ps.actionable:
#             for a in ps.actionable:
#                 print(f"       • {a}")
#         else:
#             print("       (none)")
#
#         print()
#
# pretty_print_user_summaries(p_result)


# ==============================================================================================
# Project Analyst
# ==============================================================================================
#
# sample_project_data = {
#     "project_name": "Alpha Revamp Initiative",
#
#     "meetings": [
#         {
#             "meeting_name": "Sprint Planning - Week 1",
#             "meeting_time": "2025-12-01 10:00:00",
#             "participants": ["John Doe", "Sarah Smith", "Michael Lee"],
#             "summary_points": [
#                 "Backend authentication refactor approved for this sprint.",
#                 "Sarah will complete API gateway integration by Thursday.",
#                 "Risk identified: delayed staging environment access might block QA."
#             ]
#         },
#         {
#             "meeting_name": "Sprint Review - Week 1",
#             "meeting_time": "2025-12-05 16:00:00",
#             "participants": ["John Doe", "Sarah Smith", "Michael Lee", "Aisha Khan"],
#             "summary_points": [
#                 "Dashboard UI redesign completed and demonstrated successfully.",
#                 "API gateway integration is 90% finished; only testing remains.",
#                 "No major blockers reported; team is ahead of planned velocity."
#             ]
#         }
#     ],
#
#     "user_analysis": [
#         {
#             "meeting_name": "Sprint Planning - Week 1",
#             "participant_summaries": [
#                 {
#                     "participant_name": "Sarah Smith",
#                     "key_updates": ["API gateway integration scheduled for completion by Thursday"],
#                     "roadblocks": ["Waiting for staging access approval"],
#                     "actionable": ["Follow up with DevOps on staging access", "Complete API gateway tasks"]
#                 },
#                 {
#                     "participant_name": "Michael Lee",
#                     "key_updates": ["UI redesign prototype ready for review"],
#                     "roadblocks": [],
#                     "actionable": ["Final polish before end of week demo"]
#                 }
#             ]
#         },
#         {
#             "meeting_name": "Sprint Review - Week 1",
#             "participant_summaries": [
#                 {
#                     "participant_name": "Aisha Khan",
#                     "key_updates": ["Analytics module integration test successful"],
#                     "roadblocks": [],
#                     "actionable": ["Prepare documentation for release notes"]
#                 },
#                 {
#                     "participant_name": "John Doe",
#                     "key_updates": ["Team velocity metrics improved by 12%"],
#                     "roadblocks": [],
#                     "actionable": ["Prepare next sprint board"]
#                 }
#             ]
#         }
#     ]
# }
#
# project_summary_agent = ProjectSummaryAgent(model=llm, tools= [])
#
# project_result = asyncio.run(project_summary_agent.agenerate_project_summary(project_data=sample_project_data))
#
#
# print(project_result)
#


# ======================================================================================================
# Testing add_transcript_to_mongo function if working to upload the transcript
# =======================================================================================================

# from src.utils.store_to_mongodb import extract_transcripts, process_transcript, add_transcript_to_mongo


# transcript_path = r"C:\Users\mohds\PycharmProjects\OrbitMeetAI\SampleData\Transcripts\ProjectPhoenix.docx"

# transcript = extract_transcripts([transcript_path])
# meta = process_transcript(transcript)
# save_transcript = add_transcript_to_mongo(transcript_path)

# print(save_transcript)


# =================================================================================================================
# testing email connections
# =================================================================================================================
#
# import os
# import ssl
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from dotenv import load_dotenv
#
# load_dotenv()
#
# SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
# SMTP_EMAIL = os.getenv("SMTP_EMAIL")
# SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
#
# def send_email_test():
#     print("SMTP TEST STARTED")
#     print(f"SERVER: {SMTP_SERVER}")
#     print(f"PORT: {SMTP_PORT}")
#     print(f"EMAIL: {SMTP_EMAIL}")
#
#     msg = MIMEMultipart("alternative")
#     msg["From"] = SMTP_EMAIL
#     msg["To"] = SMTP_EMAIL   # send to yourself
#     msg["Subject"] = "SMTP Test Email"
#
#     msg.attach(MIMEText("<h2>This is a test email</h2>", "html"))
#
#     try:
#         context = ssl.create_default_context()
#         print("Connecting via SSL...")
#
#         with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
#             print("Connected! Logging in...")
#             server.login(SMTP_EMAIL, SMTP_PASSWORD)
#             print("Login successful! Sending email...")
#             server.sendmail(SMTP_EMAIL, SMTP_EMAIL, msg.as_string())
#
#         print("Email sent.")
#     except Exception as e:
#         print("ERROR:", e)
#
# if __name__ == "__main__":
#     send_email_test()

# =================================================================================================
# Test mongo client only
# =================================================================================================

import os
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

def test_mongo():
    print("\n=== MongoDB Connection Test ===")
    print(f"Using URI: {MONGO_URI}\n")

    try:
        client = MongoClient(
            MONGO_URI,
            tls=True,
            tlsCAFile=certifi.where()
        )

        # Trigger connection by listing databases
        dbs = client.list_database_names()
        print("✔ Connection successful!")
        print("Databases:", dbs)

    except Exception as e:
        print("\n✘ Connection failed!")
        print("Error:", e)

if __name__ == "__main__":
    test_mongo()
