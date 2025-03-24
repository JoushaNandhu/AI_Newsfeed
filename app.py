import json
import datetime
import time
import re
import requests
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Get API key from environment variables
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")

# Function to extract JSON from text that might have extra content
def extract_json(text):
    # First try direct parsing
    try:
        return json.loads(text)
    except:
        pass
    
    # Try to find JSON content using regex pattern for outermost json object
    pattern = r'(\{[\s\S]*\})'
    matches = re.findall(pattern, text)
    
    if matches:
        for potential_json in matches:
            try:
                return json.loads(potential_json)
            except:
                continue
    
    # Try to clean markdown and other formatting
    try:
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Try to parse the cleaned text
        return json.loads(text)
    except Exception as e:
        print(f"Error parsing API response: {str(e)}. Creating empty result structure.")
        return {"news_items": [], "total_found": 0}

# Function to call Perplexity API
def call_perplexity_api(prompt):
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
            {"role": "system", "content": "You are an AI research system that identifies worldwide AI developments and news. You respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return content
        else:
            print(f"Error from Perplexity API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error calling Perplexity API: {str(e)}")
        return None

# Function to gather AI news
def gather_ai_news(days_back):
    # Calculate date range
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days_back)
    
    # Prompt for the LLM
    prompt = f"""
    You are an AI news aggregator with access to worldwide information sources. Find and report ONLY the most important AI developments and updates from the last {days_back} days (from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}).

    CRUCIAL INSTRUCTIONS:
    1. Report the top 10-15 AI-related news and developments without limiting to a specific number
    2. Focus on these categories of AI news:
       - Major AI model releases
       - Significant AI research breakthroughs
       - AI regulatory developments and policy changes
       - Important AI business news (mergers, acquisitions, significant investments)
       - AI applications in healthcare, climate, etc.
       - AI ethics concerns or controversies
    
    3. FILTERING REQUIREMENTS - DO NOT include:
       - Minor product updates
       - Opinion articles without factual content
       - Speculative pieces without substantiated claims
       - General tech news not directly related to AI
       - Redundant news covering the same story
    
    4. For each news item, provide:
       - Headline: Clear, concise headline
       - Description: 2-3 sentence summary of the key points
       - Source: Name of the source organization/website
       - Publication date: Format "Month DD, YYYY"
       - Category: One of [Research, Business, Regulation, Ethics, Application, Model]
       - Tags: Keywords related to the news
    
    RESPOND WITH ONLY VALID JSON in this exact structure:
    {
      "news_items": [
        {
          "headline": "Example AI Headline",
          "description": "A 2-3 sentence description of the news item. This should be concise but informative.",
          "source": "Source Organization",
          "published_date": "March 20, 2025",
          "category": "Research", 
          "tags": ["OpenAI", "GPT-5", "Large Language Models"]
        },
        ... (additional items)
      ], 
      "total_found": 15
    }
    """
    
    try:
        # Call the Perplexity API
        content = call_perplexity_api(prompt)
        if not content:
            return {"news_items": [], "total_found": 0}
        
        # Parse the JSON
        result = extract_json(content)
        
        # Ensure we have news_items
        if "news_items" not in result:
            if isinstance(result, list):
                return {"news_items": result, "total_found": len(result)}
            else:
                return {"news_items": [], "total_found": 0}
        
        # Ensure the "total_found" field exists and is set correctly
        if "total_found" not in result:
            result["total_found"] = len(result["news_items"])
        
        return result
    except Exception as e:
        print(f"Error gathering AI news: {str(e)}")
        return {"news_items": [], "total_found": 0}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news', methods=['POST'])
def get_news():
    data = request.json
    days_back = data.get('days_back', 3)
    
    # Gather AI news
    result = gather_ai_news(days_back)
    
    return jsonify(result)

# This is needed for Vercel
if __name__ == '__main__':
    app.run()
