from config import *
import google.generativeai as genai


genai.configure(api_key=KEY)
global model 
model = genai.GenerativeModel('gemini-1.0-pro-latest')

# function called when this plugin is executed
def execute(intent, entitie, prompt):
    """
    The function called when this plugin is executed

    Inputs:
     - intent: Stringified intent
     - entities: Dictionary containing stringified entities and their content

    Outputs:
     - command: Dictionary containing the plugin's responce in natural language
    """
    response = model.generate_content(prompt)
    
    return {
        "response": response.text
    }

