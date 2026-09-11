import os
import hashlib
import sqlite3
from datetime import datetime
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

def _get_db_connection():
    """Get database connection."""
    from database import get_db_connection
    return get_db_connection()

def _hash_prompt(prompt: str) -> str:
    """Create a hash of the prompt for quick lookup."""
    return hashlib.sha256(prompt.encode()).hexdigest()

def _get_cached_insight(prompt_hash: str):
    """Retrieve a cached insight from the database."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT insight_text, usage_count FROM ai_insights WHERE prompt_hash = ?",
            (prompt_hash,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            insight_text, usage_count = result
            # Update usage count
            conn = _get_db_connection()
            conn.execute(
                "UPDATE ai_insights SET usage_count = ?, updated_at = ? WHERE prompt_hash = ?",
                (usage_count + 1, datetime.now().isoformat(timespec="seconds"), prompt_hash)
            )
            conn.commit()
            conn.close()
            return insight_text, True  # True indicates it's cached
        return None, False
    except Exception as e:
        print(f"Error retrieving cached insight: {e}")
        return None, False

def _store_insight(prompt: str, insight_text: str, view_type: str = "analytics", metric_period: str = None):
    """Store a generated insight in the database."""
    try:
        prompt_hash = _hash_prompt(prompt)
        conn = _get_db_connection()
        
        conn.execute(
            """INSERT OR IGNORE INTO ai_insights 
               (prompt_hash, prompt, insight_text, view_type, metric_period, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                prompt_hash,
                prompt,
                insight_text,
                view_type,
                metric_period,
                datetime.now().isoformat(timespec="seconds"),
                datetime.now().isoformat(timespec="seconds")
            )
        )
        conn.commit()
        conn.close()
        return prompt_hash
    except Exception as e:
        print(f"Error storing insight: {e}")
        return None

def get_ai_insight(prompt, view_type: str = "analytics", metric_period: str = None, force_refresh: bool = False):
    """
    Sends a prompt to Gemini and returns the response.
    If a similar insight exists in the database and force_refresh is False, reuse it.
    
    Args:
        prompt: The prompt to send to the AI
        view_type: Type of view generating the insight (e.g., 'analytics', 'dashboard')
        metric_period: The metric period (e.g., 'weekly', 'monthly')
        force_refresh: If True, generate new insight even if cached version exists
    """
    prompt_hash = _hash_prompt(prompt)
    
    # Try to get cached insight if not forcing refresh
    if not force_refresh:
        cached_insight, is_cached = _get_cached_insight(prompt_hash)
        if cached_insight:
            print(f"Using cached insight (accessed {_get_usage_count(prompt_hash)} times)")
            return cached_insight
    
    # If not cached or force refresh, generate new insight
    is_configured = setup_gemini()
    
    if not is_configured:
        return "Error: GEMINI_API_KEY is missing. Please set it in your terminal."
        
    try:
        # Initialize the current stable Gemini Flash model
        model = genai.GenerativeModel('gemini-3.7-flash')
        
        # Generate the text
        response = model.generate_content(prompt)
        insight_text = response.text
        
        # Store the new insight in database
        _store_insight(prompt, insight_text, view_type, metric_period)
        
        return insight_text
        
    except Exception as e:
        return f"An error occurred while connecting to AI: {str(e)}"

def _get_usage_count(prompt_hash: str) -> int:
    """Get the usage count of a cached insight."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT usage_count FROM ai_insights WHERE prompt_hash = ?", (prompt_hash,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except:
        return 0

def get_all_insights(view_type: str = None):
    """Retrieve all stored insights, optionally filtered by view type."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        if view_type:
            cursor.execute(
                "SELECT id, prompt, insight_text, view_type, metric_period, usage_count, created_at FROM ai_insights WHERE view_type = ? ORDER BY usage_count DESC, updated_at DESC",
                (view_type,)
            )
        else:
            cursor.execute(
                "SELECT id, prompt, insight_text, view_type, metric_period, usage_count, created_at FROM ai_insights ORDER BY usage_count DESC, updated_at DESC"
            )
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Error retrieving insights: {e}")
        return []

def delete_insight(insight_id: int):
    """Delete a stored insight by ID."""
    try:
        conn = _get_db_connection()
        conn.execute("DELETE FROM ai_insights WHERE id = ?", (insight_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting insight: {e}")
        return False