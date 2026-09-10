import os
import google.generativeai as genai

def setup_gemini():
    """Configures the Gemini API using the environment variable."""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # Check if the key exists
    if not api_key:
        return False
        
    # Clean up the key if Windows added extra quotes
    if api_key.startswith('"') and api_key.endswith('"'):
        api_key = api_key[1:-1]
        
    genai.configure(api_key=api_key)
    return True

def get_ai_insight(prompt):
    """Sends a prompt to Gemini and returns the response."""
    is_configured = setup_gemini()
    
    if not is_configured:
        return "Error: GEMINI_API_KEY is missing. Please set it in your terminal."
        
    try:
        # Initialize the current stable Gemini Flash model
        model = genai.GenerativeModel('gemini-3.7-flash')
        
        # Generate and return the text
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"An error occurred while connecting to AI: {str(e)}"