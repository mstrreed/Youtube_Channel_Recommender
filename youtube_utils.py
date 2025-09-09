# youtube_utils.py

import googleapiclient.discovery
import googleapiclient.errors
import time
from typing import List

# (The existing functions `get_youtube_client` and `make_api_call_with_backoff` remain the same)

def get_youtube_client(api_key: str):
    """
    Creates and returns a YouTube API client object.
    """
    api_service_name = "youtube"
    api_version = "v3"
    youtube_client = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=api_key
    )
    return youtube_client

def make_api_call_with_backoff(youtube_client, method: str, **kwargs):
    """
    Makes an API call with exponential backoff to handle rate limits.
    """
    retries = 0
    max_retries = 5
    initial_delay = 1
    while retries < max_retries:
        try:
            request = getattr(youtube_client, method)().list(**kwargs)
            response = request.execute()
            print(f"Successfully made API call for {method}.")
            return response
        except googleapiclient.errors.HttpError as e:
            if e.resp.status in [403, 429]:
                print(f"Rate limit exceeded (HTTP {e.resp.status}). Retrying in {initial_delay} seconds...")
                time.sleep(initial_delay)
                initial_delay *= 2
                retries += 1
            else:
                raise
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    print("Maximum retries reached. Exiting.")
    return None

def get_channels_data(api_key: str, keywords: List[str], language: str, country: str, channel_limit: int):
    """
    Searches for YouTube channels based on keywords, language, and country,
    fetches their details, and returns them as a list of dictionaries,
    up to the specified channel_limit.
    """
    youtube = get_youtube_client(api_key)
    
    channel_ids = set()
    
    # Step 1: Search for all relevant channels
    print("Searching for channels...")
    for keyword in keywords:
        print(f"\n--- Searching with keyword: '{keyword}' ---")
        next_page_token = None
        while True:
            if len(channel_ids) >= channel_limit:
                print(f"Channel limit of {channel_limit} reached. Stopping search.")
                break
            
            search_response = make_api_call_with_backoff(
                youtube,
                method='search',
                part='snippet',
                q=keyword,
                type='channel',
                regionCode=country,
                relevanceLanguage=language,
                maxResults=50,
                pageToken=next_page_token
            )
            
            if not search_response or 'items' not in search_response:
                break
            
            for item in search_response.get('items', []):
                channel_ids.add(item['id']['channelId'])
            
            print(f"Found {len(channel_ids)} unique channel IDs so far.")
            
            next_page_token = search_response.get('nextPageToken')
            if not next_page_token:
                print(f"Finished searching all pages for '{keyword}'.")
                break
            time.sleep(2)
        if len(channel_ids) >= channel_limit:
            break
            
    if not channel_ids:
        print("No unique channel IDs found.")
        return []
    
    unique_channel_ids = list(channel_ids)
    
    # Trim the list to the specified limit
    unique_channel_ids = unique_channel_ids[:channel_limit]
    
    print(f"\nTotal {len(unique_channel_ids)} unique channels found. Now fetching details...")
    
    # Step 2: Fetch detailed information for each channel in batches
    channel_details = []
    batch_size = 50
    for i in range(0, len(unique_channel_ids), batch_size):
        batch_ids = unique_channel_ids[i:i + batch_size]
        ids_string = ",".join(batch_ids)
        time.sleep(2)
        print(f"Fetching details for batch {int(i/batch_size) + 1}...")
        
        channels_response = make_api_call_with_backoff(
            youtube,
            method='channels',
            part='snippet,statistics,brandingSettings',
            id=ids_string
        )

        if channels_response and 'items' in channels_response:
            for channel_info in channels_response['items']:
                snippet = channel_info.get('snippet', {})
                statistics = channel_info.get('statistics', {})
                branding_settings = channel_info.get('brandingSettings', {})
                
                channel_details.append({
                    'title': snippet.get('title', ''),
                    'custom_url': branding_settings.get('channel', {}).get('customUrl', ''),
                    'subscribers': statistics.get('subscriberCount', 'N/A'),
                    'videos': statistics.get('videoCount', 'N/A'),
                    'description': snippet.get('description', ''),
                    'channel_url': f"https://www.youtube.com/channel/{channel_info.get('id', '')}",
                    'published_date': snippet.get('publishedAt', 'N/A'),
                    'channel_id': channel_info.get('id', 'N/A')
                })
    
    return channel_details