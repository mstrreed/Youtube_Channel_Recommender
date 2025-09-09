# main.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import io

# Import your refactored functions
from youtube_utils import get_channels_data

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Renders the home page with the input form.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search-channels/")
async def search_channels(
    api_key: str = Form(...),
    keywords: str = Form(...),
    language: str = Form(...),
    country: str = Form(...),
    channel_limit: int = Form(...) # New parameter for the channel limit
):
    """
    Accepts form data, retrieves channel data, and returns a CSV file.
    """
    try:
        # Split the keywords string into a list
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        
        # Get the data using your refactored function
        channel_data = get_channels_data(api_key, keyword_list, language, country, channel_limit)
        
        if not channel_data:
            return HTMLResponse("<h1>No channels found. Please try different keywords or an API key.</h1>")

        # Convert the list of dictionaries to a Pandas DataFrame
        df = pd.DataFrame(channel_data)
        
        # Generate the CSV in-memory
        csv_stream = io.StringIO()
        df.to_csv(csv_stream, index=False)
        
        # Create a StreamingResponse with the CSV data
        response = StreamingResponse(iter([csv_stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=youtube_channels.csv"
        return response

    except Exception as e:
        print(f"An error occurred: {e}")
        return HTMLResponse(f"<h1>An error occurred: {e}</h1>", status_code=500)