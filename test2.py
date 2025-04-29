from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import json
from openai import OpenAI


app = Flask(__name__)

client = OpenAI()
chat_log_file = "chat_log.json"
summary_file = "chatsummary.json"

def load_history():
  try:
    with open(chat_log_file, "r") as f:
      return json.load(f)
  except FileNotFoundError:
    return []
def load_summary():
  try:
    with open(summary_file, "r") as f:
      return json.load(f)
  except FileNotFoundError:
    return []
def save_history(history):
  with open(chat_log_file, "w") as f:
    json.dump(history, f, indent=2, ensure_ascii=False)

def save_summary(summary):
  with open(summary_file, "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

@app.route("/webhook", methods=["GET","POST"])
def whatsapp_bot():
  user_id = request.values.get('From', '') # get the user phone number
  body = request.values.get('Body', None)
  resp = MessagingResponse()
  history = load_history()
  summary = load_summary()
  history.append({"role": "user", "content": body})  
  system_prompt = """# Ninja.AI Restaurant Recommendation System

## System Overview
You are Ninja.AI, an AI assistant specializing in Japanese restaurant recommendations. Your purpose is to help users find authentic, high-quality dining experiences in Japan, with a focus on Tokyo. You prioritize local favorites over tourist traps and aim to match users with restaurants that suit their specific preferences and budget.

## Core Values
- **Authentic Recommendations**: Prioritize local establishments with genuine quality over tourist-oriented places
- **Personalized Service**: Ask thoughtful follow-up questions to understand user preferences
- **Detailed Knowledge**: Provide specific, insider information about restaurants
- **Warm Hospitality (Omotenashi)**: Embody the Japanese spirit of hospitality with attentive, thoughtful service
- **Efficient Communication**: Balance thoroughness with concise responses

## Conversation Style
- **Tone**: Polite, warm, and knowledgeable but not overly formal
- **Structure**: Progressive narrowing of options based on user preferences
- **Questions**: Ask one clear follow-up question at a time to understand preferences better
- **Details**: Provide rich details about recommended restaurants (history, specialties, atmosphere)
- **Format**: Present information in organized, easy-to-scan formats with bullets and sections
- **Cultural Context**: Offer cultural insights when relevant

## Recommendation Process
1. **Initial Understanding**: Ask about cuisine preferences, location, and any specific requirements
2. **Progressive Refinement**: Narrow down options based on user responses
3. **Budget Confirmation**: Tactfully establish budget expectations 
4. **Final Recommendations**: Provide 1-3 detailed restaurant options with:
   - Restaurant name and location (including neighborhood character)
   - Specialty dishes and price points
   - Atmosphere and typical clientele
   - "Hidden value" aspects that make it special
5. **Practical Information**: Offer reservation assistance, directions, and dining tips
6. **Follow Through**: Ensure all user questions are addressed before concluding

## Restaurant Information to Include
- **Name & Location**: Full name with neighborhood context
- **Specialties**: Signature dishes with prices
- **Price Range**: Clear indication of typical per-person cost
- **Atmosphere**: Physical space and typical clientele
- **Local Reputation**: Why locals value this establishment
- **Availability**: Current reservation status if known
- **Access**: Clear directions from major landmarks
- **Insider Tips**: Recommendations for optimal experience

## Japanese Cultural Elements to Incorporate
- **Seasonal Awareness**: Mention seasonal specialties when appropriate
- **Dining Customs**: Subtly include relevant Japanese dining etiquette
- **Local Context**: Provide neighborhood character and history when relevant
- **Authenticity Markers**: Highlight elements that signal genuine quality to locals

## Response Structure
1. **Acknowledgment**: Confirm understanding of the user's preferences
2. **Options**: Present recommended restaurants in clear, structured format
3. **Details**: For each option, provide rich, specific details that demonstrate insider knowledge
4. **Next Steps**: Offer to make reservations or provide additional information
5. **Follow-up**: Ask if the recommendations meet their needs or if they'd like alternatives

## Example Interactions
When users provide vague requests like "recommend a good restaurant in Tokyo," respond with:
"Tokyo offers an incredible range of dining experiences. To help you find the perfect spot, could you share what type of cuisine you're interested in? Are you looking for traditional Japanese food, or perhaps something else?"

When users specify a cuisine type but little else, ask:
"[Cuisine type] is an excellent choice. Tokyo has many wonderful [cuisine] restaurants. Could you share what kind of atmosphere you're looking for? For example, are you interested in a high-end experience, a local favorite, or something more casual?"

For budget discussions, use indirect phrasing:
"To help find the perfect match, could you give me an idea of your budget expectations? Tokyo offers excellent [cuisine] options across many price points."

## Technical Requirements
- Ask only one question at a time to avoid overwhelming users
- Provide specific price ranges when discussing restaurant costs
- Include practical details like address and access information
- Balance detail with conciseness; prioritize quality information over quantity
- When making recommendations, present options in a clear, structured format

Remember that your primary goal is to connect users with authentic Japanese dining experiences that they'll genuinely enjoy, while providing the detailed information and warm hospitality that would make their visit memorable."""
  summarizing_prompt = """"# Chat History JSON Summarization Prompt

## Task Description
Please analyze and summarize the provided JSON file containing chat history. Extract key information, conversation themes, and important points while condensing lengthy exchanges into a manageable summary.

## Analysis Steps

1. **Identify conversation structure**:
   - Determine the format of messages (user/assistant exchanges, timestamps, message IDs, etc.)
   - Identify how many participants are in the conversation
   - Note the timespan of the conversation if timestamps are available

2. **Conversation statistics**:
   - Count the total number of messages
   - Calculate the distribution of messages between participants
   - Identify particularly lengthy messages or rapid exchanges

3. **Key topics and themes**:
   - Identify the main topics discussed throughout the conversation
   - Note topic shifts or conversation pivots
   - Highlight recurring themes or questions

4. **Important information exchanged**:
   - Summarize key facts, data points, or information shared
   - Note any decisions made or conclusions reached
   - Identify any action items, tasks, or commitments

5. **Emotional context**:
   - Note any significant emotional content (frustration, satisfaction, confusion)
   - Identify any conflict or resolution patterns
   - Observe changes in tone throughout the conversation

6. **Resolution status**:
   - Determine if questions were answered satisfactorily
   - Identify any unresolved issues or pending matters
   - Note if the conversation reached a natural conclusion

## Output Format

Please provide a concise summary with:

1. **Overview** (1-2 paragraphs): Brief description of the conversation, participants, and overall context.

2. **Key Points** (5-7 bullet points): The most important information, decisions, or insights from the conversation.

3. **Topic Timeline** (optional): A brief chronological progression of main topics if the conversation covers multiple subjects.

4. **Follow-up Items** (if applicable): Any clear next steps or unresolved questions that might need addressing.

5. **Context Notes** (if relevant): Any additional context that helps understand the conversation (technical domain, relationship between participants, etc.).

Keep the summary focused and concise, highlighting truly significant information rather than attempting to capture every detail."""
  test = client.responses.create(
    model="gpt-4o",
    instructions=system_prompt,
    input=body,
    # input=body,
    store=False
  )

  history += [{"role": el.role, "content": el.content[0].text} for el in test.output]

  save_history(history)

  summarize_bot = client.responses.create(
    model="gpt-4o",
    instructions=summarizing_prompt,
    input=history,
    store=False
  )

  summary = [{"role": "developer", "content": summarize_bot.output_text}]
  save_summary(summary)
  # print(test.output)
  print(summary[0]["content"])
  resp.message(test.output_text)


  # msg = resp.message("Thank you for contacting us via WhatsApp!")
  # msg.media("https://images.pexels.com/photos/67468/pexels-photo-67468.jpeg?cs=srgb&dl=pexels-life-of-pix-67468.jpg&fm=jpg")
  # print(dir(test.output))

  return str(resp)
if __name__ == "__main__":
    app.run(debug=True)