# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []


from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
from mistralai import Mistral


class ActionFetchFormattedSymptoms(Action):
    def name(self) -> Text:
        return "action_fetch_formatted_symptoms"

    # Step 1: Make the API Call to Retrieve Data
    # returns a dictionary
    def retrieve_health_condition_data(self, condition: Text, api_key: Text) -> Dict:
        # Define the health API URL
        url = f"https://int.api.service.nhs.uk/nhs-website-content/conditions/{condition}/?modules=true"
        
        # Define the API URL
        headers = {
            "Content-Type": "application/json",
            "apikey": api_key
        }
        
         # Make the API call with headers
        response = requests.get(url, headers=headers)
        # Check the response status code
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    
    # Step2: Extract All Relevant Sections
    # Note: data = retrieve_health_condition_data(condition, api_key)
    def extract_sections(self, data: Dict) -> List[Dict]:
        sections = []
        for module in data.get('modules', []):
            for part in module.get('hasPart', []):
                sections.append({
                    'headline': part.get('headline', ''),
                    'text': part.get('text', '')
                })
        return sections

    # Step 3: Send Each Section to an LLM API for Formatting
    # Note: sections 
    def format_text_with_llm_batch(self, sections: List[Dict], llm_api_key: Text) -> Text:
        # Initialize the Mistral client
        client = Mistral(api_key=llm_api_key)
        model = "mistral-large-latest"
        
        # Combine sections into a single message (or split into batches if too large)
        combined_text = "\n\n".join([f"### {section['headline']}\n{section['text']}" for section in sections])
        
        # Format text using the chat.complete method
        chat_response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"Format the following text into a user-friendly summary:\n\n{combined_text}",
                },
            ],
        )

        # Check if the response contains the formatted content
        if chat_response.choices:
            # Extract and return the formatted content
            return chat_response.choices[0].message.content
        else:
            return "Formatting failed. Mistral returned no choices."

    def run(self, 
            dispatcher: CollectingDispatcher, 
            tracker: Tracker, 
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        condition = tracker.get_slot("condition")
        if not condition:
            dispatcher.utter_message("Please specify the health condition.")
            return []

        api_key = "uLVy9pJdtxUrGvTMcUcHghcIxaknLZ7H"  # NHS API key
        llm_api_key = "4uh77khK3mRVeSihTvEjiWCeZEoISryp"  # Mistral LLM API key

        # Retrieve data for the health condition
        data = self.retrieve_health_condition_data(condition, api_key)
        if data:
            # Extract all relevant sections
            sections = self.extract_sections(data)
            # Format and Display the formatted text to the user
            formatted_response = self.format_text_with_llm_batch(sections, llm_api_key)
            dispatcher.utter_message(formatted_response)
        else:
            dispatcher.utter_message(f"Sorry, I couldn't fetch data for {condition}. Please try again.")
        
        return []
