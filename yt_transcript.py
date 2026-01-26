"""
YouTube Transcript Fetcher

This module provides functionality to fetch transcripts from YouTube videos
using the youtube-transcript-api library.

Documentation: https://pypi.org/project/youtube-transcript-api/
"""

import re
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from various YouTube URL formats.

    Args:
        url: YouTube video URL

    Returns:
        Video ID if found, None otherwise
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_transcript(video_url: str, languages: Optional[list] = None) -> Optional[dict]:
    """
    Fetch transcript for a YouTube video.

    Args:
        video_url: YouTube video URL
        languages: List of language codes (e.g., ['en', 'ko']).
                   If None, tries to fetch in any available language.

    Returns:
        Dictionary with 'text' (full transcript), 'transcript' (list of dicts),
        'video_id', 'language', 'language_code', and 'is_generated',
        or None if transcript cannot be fetched
    """
    video_id = extract_video_id(video_url)

    if not video_id:
        print(f"Error: Could not extract video ID from URL: {video_url}")
        return None

    try:
        # Instantiate the API
        ytt_api = YouTubeTranscriptApi()

        # First, list available transcripts
        try:
            transcript_list_obj = ytt_api.list(video_id)
            available_transcripts = list(transcript_list_obj)
        except Exception as e:
            print(f"Error: Could not list transcripts for video: {video_id}")
            print(f"Details: {str(e)}")
            return None

        if not available_transcripts:
            print(f"Error: No transcripts available for video: {video_id}")
            print("This video may not have any transcripts enabled.")
            return None

        # Try to fetch transcript
        fetched_transcript = None

        if languages:
            # Try to fetch with specified languages
            try:
                fetched_transcript = ytt_api.fetch(video_id, languages=languages)
            except NoTranscriptFound:
                print(f"Warning: Requested languages {languages} not found.")
                print(f"Available transcripts for video {video_id}:")
                for t in available_transcripts:
                    print(f"  - {t.language} ({t.language_code}) - {'Generated' if t.is_generated else 'Manual'}")
                # Try to use the first available transcript
                transcript = available_transcripts[0]
                print(f"\nUsing available transcript: {transcript.language} ({transcript.language_code})")
                fetched_transcript = transcript.fetch()
        else:
            # No language specified - try English first, then any available
            try:
                fetched_transcript = ytt_api.fetch(video_id, languages=['en'])
            except NoTranscriptFound:
                # English not available, use first available transcript
                transcript = available_transcripts[0]
                print(f"English transcript not available. Using: {transcript.language} ({transcript.language_code})")
                fetched_transcript = transcript.fetch()

        # Get raw data as list of dictionaries
        transcript_list = fetched_transcript.to_raw_data()

        # Combine all transcript entries into a single text
        full_text = ' '.join([entry['text'] for entry in transcript_list])

        return {
            'text': full_text,
            'transcript': transcript_list,
            'video_id': fetched_transcript.video_id,
            'language': fetched_transcript.language,
            'language_code': fetched_transcript.language_code,
            'is_generated': fetched_transcript.is_generated
        }

    except TranscriptsDisabled:
        print(f"Error: Transcripts are disabled for video: {video_id}")
        return None
    except VideoUnavailable:
        print(f"Error: Video is unavailable: {video_id}")
        return None
    except Exception as e:
        print(f"Error fetching transcript: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def get_transcript_text(video_url: str, languages: Optional[list] = None) -> Optional[str]:
    """
    Get transcript as plain text string.

    Args:
        video_url: YouTube video URL
        languages: List of language codes (e.g., ['en', 'ko'])

    Returns:
        Transcript text as string, or None if unavailable
    """
    result = get_transcript(video_url, languages)
    return result['text'] if result else None


if __name__ == "__main__":
    # Example usage
    test_url = input("Enter YouTube video URL: ").strip()

    if test_url:
        print("\nFetching transcript...")
        transcript = get_transcript(test_url)

        if transcript:
            print(f"\nVideo ID: {transcript['video_id']}")
            print(f"Language: {transcript['language']} ({transcript['language_code']})")
            print(f"Is Generated: {transcript['is_generated']}")
            print(f"\nTranscript ({len(transcript['transcript'])} entries):")
            print("-" * 50)
            print(transcript['text'])
            print("-" * 50)
        else:
            print("Failed to fetch transcript.")
    else:
        print("No URL provided.")

