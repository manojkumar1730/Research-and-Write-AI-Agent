import streamlit as st
import os
from dotenv import load_dotenv
import requests
import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError
import time
import json

# Load environment variables
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Streamlit setup
st.set_page_config(page_title="AI Research & Writing Tool", page_icon="🧠")
st.title("🧠 Simple AI Research & Writing Tool")
st.write("Generate research and articles using FREE Groq AI (Llama/Claude models) with web search.")

# Inputs
topic = st.text_input("🔍 Enter a Topic:", "AI in Healthcare")
language = st.selectbox("🌐 Select Language:", ["English", "Kannada", "French", "German", "Chinese"])
research_depth = st.radio("📊 Research depth:", ["Basic", "Detailed"])

# Model selection with better options
model_choice = st.selectbox(
    "🤖 Select AI Model:", 
    [
        "llama-3.1-8b-instant",    # Most reliable
        "llama-3.1-70b-versatile", # Best quality  
        "llama3-8b-8192",          # Alternative
        "mixtral-8x7b-32768",      # Research optimized
        "llama3-70b-8192"          # Alternative 70B
    ]
)

# Wikipedia search helper
def wikipedia_search(topic):
    try:
        summary = wikipedia.summary(topic, sentences=3)
        page = wikipedia.page(topic)
        return {
            "summary": summary,
            "url": page.url,
            "title": page.title
        }
    except DisambiguationError as e:
        return {"summary": f"Multiple topics found: {e.options[:5]}", "url": "", "title": ""}
    except PageError:
        return {"summary": "No Wikipedia page found for this topic.", "url": "", "title": ""}

# Serper web search function
def web_search(query, num_results=5):
    if not SERPER_API_KEY:
        return []
    
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "num": num_results
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        results = response.json()
        
        search_results = []
        if 'organic' in results:
            for result in results['organic']:
                search_results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "link": result.get("link", "")
                })
        return search_results
    except Exception as e:
        st.warning(f"Web search error: {str(e)}")
        return []

# Groq API call function with detailed debugging
def call_groq_api(prompt, max_tokens=3000):
    if not GROQ_API_KEY:
        return "Error: Groq API key not found."
    
    if not GROQ_API_KEY.startswith('gsk_'):
        return "Error: Invalid Groq API key format. Key should start with 'gsk_'"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Ensure prompt isn't too long
    if len(prompt) > 15000:  # Conservative limit
        prompt = prompt[:15000] + "\n\n[Content truncated due to length]"
    
    data = {
        "model": model_choice,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": min(max_tokens, 4000),  # More conservative limit
        "temperature": 0.7,
        "top_p": 1.0,
        "stream": False
    }
    
    # Debug info code fully removed
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        
    # Debug info code fully removed
        
        # Handle different error cases
        if response.status_code == 400:
            try:
                error_info = response.json()
                error_message = error_info.get('error', {}).get('message', 'Unknown 400 error')
                error_type = error_info.get('error', {}).get('type', 'Unknown type')
                
                # Common 400 errors and solutions
                if "model" in error_message.lower():
                    return f"Error: Model '{model_choice}' not available. Try: llama-3.1-8b-instant"
                elif "token" in error_message.lower():
                    return f"Error: Token limit issue. {error_message}"
                elif "rate" in error_message.lower():
                    return f"Error: Rate limit exceeded. {error_message}"
                else:
                    return f"Error 400: {error_message} (Type: {error_type})"
                    
            except json.JSONDecodeError:
                return f"Error 400: Invalid request format. Response: {response.text[:200]}"
                
        elif response.status_code == 401:
            return "Error 401: Invalid API key. Please check your Groq API key."
        elif response.status_code == 429:
            return "Error 429: Rate limit exceeded. Please wait a moment and try again."
        elif response.status_code != 200:
            return f"Error {response.status_code}: {response.text[:300]}"
        
        result = response.json()
        
        if 'choices' not in result or len(result['choices']) == 0:
            return f"Error: Unexpected response format: {result}"
            
        return result["choices"][0]["message"]["content"]
        
    except requests.exceptions.Timeout:
        return "Error: Request timed out. Groq API is taking too long to respond."
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to Groq API. Check your internet connection."
    except requests.exceptions.RequestException as e:
        return f"Error: Network issue: {str(e)}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON response from Groq API: {str(e)}"
    except KeyError as e:
        return f"Error: Missing field in API response: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected issue: {str(e)}"

# Research function
def conduct_research(topic):
    st.write("🔍 **Step 1: Conducting web research...**")
    
    # Perform web searches
    search_queries = [
        f"{topic} latest developments 2024",
        f"{topic} trends applications",
        f"{topic} challenges opportunities future"
    ]
    
    all_results = []
    for query in search_queries:
        results = web_search(query, 3)
        all_results.extend(results)
        time.sleep(1)  # Rate limiting
    
    # Get Wikipedia info
    wiki_info = wikipedia_search(topic)
    
    # Compile research data
    research_data = {
        "web_results": all_results,
        "wikipedia": wiki_info,
        "search_queries": search_queries
    }
    
    st.success(f"✅ Found {len(all_results)} web sources + Wikipedia reference")
    return research_data

# Generate research report
def generate_research_report(topic, research_data):
    st.write("📝 **Step 2: Analyzing research and generating report...**")
    
    # Prepare research context
    web_context = "\n".join([
        f"Title: {result['title']}\nContent: {result['snippet']}\nSource: {result['link']}\n"
        for result in research_data['web_results'][:10]  # Limit to avoid token limits
    ])
    
    wiki_context = f"Wikipedia Summary: {research_data['wikipedia']['summary']}"
    
    research_prompt = f"""
    You are a senior researcher. Analyze the following information about "{topic}" and create a comprehensive research report.

    WEB SEARCH RESULTS:
    {web_context}

    WIKIPEDIA REFERENCE:
    {wiki_context}

    Create a structured research report that includes:
    1. Executive Summary
    2. Key Findings and Current Trends
    3. Applications and Use Cases
    4. Challenges and Limitations
    5. Future Outlook
    6. Key Statistics (if available)
    7. Important Sources

    Make the report informative, well-organized, and based on the provided research data.
    Focus on accuracy and cite relevant information from the sources.
    """
    
    research_report = call_groq_api(research_prompt, max_tokens=2500)
    return research_report

# Generate final article
def generate_article(topic, language, research_report, research_depth):
    st.write(f"✍️ **Step 3: Writing comprehensive article in {language}...**")
    
    depth_instruction = ""
    if research_depth == "Detailed":
        depth_instruction = "Create a detailed, comprehensive article (1500-2000 words) with in-depth analysis."
    else:
        depth_instruction = "Create a well-structured article (800-1200 words) covering the key points."
    
    article_prompt = f"""
    You are a professional content writer. Based on the research report below, write an engaging article about "{topic}" in {language}.

    RESEARCH REPORT:
    {research_report}

    REQUIREMENTS:
    - Write entirely in {language} language
    - {depth_instruction}
    - Structure: Introduction, Main Body (3-4 sections), Conclusion
    - Use clear headings and subheadings
    - Make it accessible to both technical and general audiences
    - Include relevant examples and insights from the research
    - Ensure proper flow and engaging style
    - Add a compelling introduction and strong conclusion

    Create a publication-ready article that effectively communicates the topic's importance and implications.
    """
    
    article = call_groq_api(article_prompt, max_tokens=3500)
    return article

# Improve article (for detailed mode)
def improve_article(article, topic, language):
    st.write("✨ **Step 4: Polishing and improving the article...**")
    
    improvement_prompt = f"""
    You are a professional editor. Review and improve the following article about "{topic}" in {language}.

    ARTICLE TO IMPROVE:
    {article}

    IMPROVEMENT TASKS:
    1. Enhance readability and flow
    2. Improve structure and organization
    3. Add better transitions between sections
    4. Ensure consistent tone and style
    5. Fix any grammar or language issues
    6. Make the content more engaging
    7. Ensure all information is well-presented
    8. Add section breaks and better formatting

    Return the improved, polished version of the article that's ready for publication.
    Maintain the same language ({language}) and overall content while making it significantly better.
    """
    
    improved_article = call_groq_api(improvement_prompt, max_tokens=4000)
    return improved_article

# Main execution
if st.button("🚀 Generate Research Article"):
    if not GROQ_API_KEY:
        st.error("❌ GROQ_API_KEY not found!")
        st.markdown("""
        **Get your FREE Groq API key:**
        1. Go to https://console.groq.com/
        2. Sign up for free (no credit card needed)
        3. Create API key
        4. Add to .env file: `GROQ_API_KEY=your_key_here`
        
        **Make sure your key starts with 'gsk_'**
        """)
        st.stop()
    
    if not GROQ_API_KEY.startswith('gsk_'):
        st.error("❌ Invalid Groq API key format!")
        st.info("Your Groq API key should start with 'gsk_'. Please check your .env file.")
        st.stop()
    
    # Test API connection
    st.info("🔧 Testing Groq API connection...")
    test_result = call_groq_api("Say 'Connection test successful'", 20)
    
    if "Error" in test_result:
        st.error("❌ Groq API connection failed!")
        st.code(test_result)
        st.markdown("""
        **Try these solutions:**
        1. **Check API key**: Make sure it starts with 'gsk_' and is correct
        2. **Try different model**: Change to 'llama-3.1-8b-instant'
        3. **Check internet**: Ensure you have stable internet connection
        4. **Wait and retry**: You might have hit rate limits
        
        **Model alternatives to try:**
        - llama-3.1-8b-instant (fastest)
        - llama3-8b-8192 (alternative)
        - mixtral-8x7b-32768 (if others fail)
        """)
        st.stop()
    
    st.success("✅ Groq API connection successful!")
    
    if not SERPER_API_KEY:
        st.warning("⚠️ SERPER_API_KEY not found. Web search will be limited.")
    
    with st.spinner("🤖 AI is working on your research article..."):
        start_time = time.time()
        
        try:
            # Step 1: Research
            research_data = conduct_research(topic)
            
            # Step 2: Generate research report
            research_report = generate_research_report(topic, research_data)
            
            if "Error" in research_report:
                st.error(f"Research failed: {research_report}")
                st.stop()
            
            # Step 3: Generate article
            article = generate_article(topic, language, research_report, research_depth)
            
            if "Error" in article:
                st.error(f"Article generation failed: {article}")
                st.stop()
            
            # Step 4: Improve article (for detailed mode)
            final_article = article
            if research_depth == "Detailed":
                final_article = improve_article(article, topic, language)
                if "Error" in final_article:
                    st.warning("Article improvement failed, using original version.")
                    final_article = article
            
            end_time = time.time()
            processing_time = round(end_time - start_time, 2)
            
            # Display results
            st.success(f"🎉 Research Article Generated Successfully! (in {processing_time} seconds)")
            
            # Show model info
            st.info(f"🤖 **Model Used:** {model_choice} | **Language:** {language} | **Depth:** {research_depth}")
            
            # Display the article
            st.subheader("📄 Generated Research Article")
            st.markdown("---")
            
            # Format and display article
            st.markdown(final_article)
            
            st.markdown("---")
            
            # Show research sources
            if research_data['web_results']:
                with st.expander("🔍 Research Sources Used", expanded=False):
                    st.write("**Web Sources:**")
                    for i, result in enumerate(research_data['web_results'][:5], 1):
                        st.write(f"{i}. **{result['title']}**")
                        st.write(f"   {result['snippet']}")
                        st.write(f"   🔗 [{result['link']}]({result['link']})")
                        st.write("")
            
            # Wikipedia reference
            if research_data['wikipedia']['summary'] and "error" not in research_data['wikipedia']['summary'].lower():
                with st.expander("📖 Wikipedia Reference", expanded=False):
                    st.write(f"**{research_data['wikipedia']['title']}**")
                    st.write(research_data['wikipedia']['summary'])
                    if research_data['wikipedia']['url']:
                        st.write(f"🔗 [Read more on Wikipedia]({research_data['wikipedia']['url']})")
            
            # Download options
            st.subheader("📥 Download Your Article")
            
            col1, col2, col3 = st.columns(3)
            
            filename_base = topic.replace(' ', '_').replace('/', '_')
            
            with col1:
                st.download_button(
                    label="📄 Download as Text",
                    data=final_article,
                    file_name=f"{filename_base}_research_article.txt",
                    mime="text/plain"
                )
            
            with col2:
                markdown_content = f"# {topic}\n\n{final_article}"
                st.download_button(
                    label="📝 Download as Markdown",
                    data=markdown_content,
                    file_name=f"{filename_base}_research_article.md",
                    mime="text/markdown"
                )
            
            with col3:
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{topic} - Research Article</title>
                    <meta charset="UTF-8">
                    <style>
                        body {{ 
                            font-family: 'Georgia', serif; 
                            max-width: 900px; 
                            margin: 0 auto; 
                            padding: 40px 20px; 
                            line-height: 1.8; 
                            color: #333;
                        }}
                        h1 {{ 
                            color: #2c3e50; 
                            border-bottom: 3px solid #3498db; 
                            padding-bottom: 15px; 
                            margin-bottom: 30px;
                        }}
                        h2 {{ 
                            color: #34495e; 
                            margin-top: 40px; 
                            margin-bottom: 20px;
                        }}
                        p {{ margin-bottom: 20px; }}
                        .meta {{ 
                            background: #f8f9fa; 
                            padding: 15px; 
                            border-left: 4px solid #3498db; 
                            margin: 20px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="meta">
                        <strong>Research Article:</strong> {topic}<br>
                        <strong>Language:</strong> {language}<br>
                        <strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}<br>
                        <strong>AI Model:</strong> {model_choice}
                    </div>
                    <h1>{topic}</h1>
                    <div style="white-space: pre-line;">{final_article}</div>
                    <hr style="margin-top: 50px;">
                    <p><small><em>Generated using AI Research & Writing Tool powered by Groq</em></small></p>
                </body>
                </html>
                """
                st.download_button(
                    label="🌐 Download as HTML",
                    data=html_content,
                    file_name=f"{filename_base}_research_article.html",
                    mime="text/html"
                )
            
            # Show research report separately
            with st.expander("📊 View Research Report", expanded=False):
                st.markdown("### Research Analysis")
                st.markdown(research_report)
        
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            st.info("Please try again or check your API keys.")

# Sidebar
st.sidebar.header("📊 Current Status")
groq_status = "✅ Connected" if GROQ_API_KEY else "❌ Missing"
serper_status = "✅ Connected" if SERPER_API_KEY else "⚠️ Optional"

st.sidebar.markdown(f"""
**API Status:**
- Groq API: {groq_status}
- Serper API: {serper_status}

**Selected Model:** {model_choice}
**Language:** {language}
""")

st.sidebar.header("🤖 Model Guide")
st.sidebar.markdown("""
**Recommended Models:**
- **llama-3.1-8b-instant**: Fastest, most reliable
- **llama-3.1-70b-versatile**: Best quality, comprehensive research
- **llama3-8b-8192**: Alternative 8B model
- **mixtral-8x7b-32768**: Excellent for research tasks
- **llama3-70b-8192**: Alternative 70B model

**Free Limits:**
- 6,000 tokens per minute
- No daily limits
- No credit card required
""")

st.sidebar.header("🛠️ Troubleshooting")
st.sidebar.markdown("""
**If you get API errors:**

1. **Check API key format:**
   - Should start with 'gsk_'
   - No extra spaces or quotes
   
2. **Common issues:**
   - Wrong model name
   - API rate limits
   - Network connectivity
   
3. **Test steps:**
   - Use 'Test Connection' button
   - Try llama-3.1-8b-instant model
   - Check .env file location
""")

if st.sidebar.button("🔄 Test Connection"):
    if GROQ_API_KEY:
        with st.sidebar.container():
            test_result = call_groq_api("Say 'Hello! API working!'", 20)
            if "working" in test_result or "Hello" in test_result:
                st.sidebar.success("✅ Groq API working!")
            else:
                st.sidebar.error("❌ Groq API issue: Try switching to: llama-3.1-8b-instant")
    else:
        st.sidebar.error("❌ No Groq API key found")