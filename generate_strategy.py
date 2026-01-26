"""
Generate Trading Strategy from YouTube Video Transcripts

This script takes a list of YouTube video links, extracts transcripts,
and uses OpenAI API to create an organized trading strategy document.
"""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from yt_transcript import get_transcript_text

# Load environment variables from .env file
load_dotenv()


def generate_strategy_from_videos(video_urls: list[str], output_dir: str = "strategy") -> str:
    """
    Generate a trading strategy from YouTube video transcripts.

    Args:
        video_urls: List of YouTube video URLs
        output_dir: Directory to save the strategy file (default: "strategy")

    Returns:
        Path to the generated strategy file
    """
    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set your OpenAI API key in the environment or .env file.")
        return None

    client = OpenAI(api_key=api_key)

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)

    # Collect transcripts from all videos
    print("Fetching transcripts from YouTube videos...")
    transcripts = []
    failed_videos = []

    for i, url in enumerate(video_urls, 1):
        print(f"\n[{i}/{len(video_urls)}] Processing: {url}")
        transcript_text = get_transcript_text(url)

        if transcript_text:
            transcripts.append({
                'url': url,
                'text': transcript_text
            })
            print(f"✓ Successfully fetched transcript ({len(transcript_text)} characters)")
        else:
            failed_videos.append(url)
            print("✗ Failed to fetch transcript")

    if not transcripts:
        print("\n❌ Error: No transcripts were successfully fetched.")
        return None

    if failed_videos:
        print(f"\n⚠️  Warning: {len(failed_videos)} video(s) failed to fetch transcripts:")
        for url in failed_videos:
            print(f"  - {url}")

    # Combine all transcripts
    print(f"\n📝 Combining {len(transcripts)} transcript(s)...")
    combined_transcripts = "\n\n---\n\n".join([
        f"Video URL: {t['url']}\n\nTranscript:\n{t['text']}"
        for t in transcripts
    ])

    # Create prompt for OpenAI
    prompt = f"""You are a trading strategy analyst. Analyze the following YouTube video transcripts about trading strategies and create a comprehensive, well-organized trading strategy document.

The strategy document should include:
1. **Executive Summary** - Brief overview of the strategy
2. **Key Concepts** - Main trading concepts discussed
3. **Entry Rules** - When to enter trades
4. **Exit Rules** - When to exit trades
5. **Risk Management** - Risk management principles mentioned
6. **Technical Indicators** - Any indicators or tools used
7. **Market Conditions** - Recommended market conditions for the strategy
8. **Implementation Steps** - Step-by-step guide to implement the strategy
9. **Notes and Considerations** - Important notes, warnings, or considerations

Format the output as a clear, professional markdown document. Be specific and actionable.

Here are the video transcripts:

{combined_transcripts}

Please create a comprehensive trading strategy document based on the above transcripts:"""

    # Call OpenAI API
    print("\n🤖 Generating strategy using OpenAI...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert trading strategy analyst who creates clear, actionable, and well-organized trading strategy documents from video transcripts."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
        )

        strategy_content = response.choices[0].message.content

        # Generate filename with date
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"strategy_{date_str}.md"
        filepath = os.path.join(output_dir, filename)

        # Save strategy to file
        with open(filepath, 'w', encoding='utf-8') as f:
            # Add header with metadata
            f.write("# Trading Strategy\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Source Videos:** {len(transcripts)} video(s)\n\n")
            for i, t in enumerate(transcripts, 1):
                f.write(f"{i}. {t['url']}\n")
            f.write("\n---\n\n")
            f.write(strategy_content)

        print(f"\n✅ Strategy saved to: {filepath}")
        return filepath

    except Exception as e:
        print(f"\n❌ Error generating strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Example usage
    video_urls = [
        # Add your YouTube video URLs here
        # "https://www.youtube.com/watch?v=example1",
        # "https://www.youtube.com/watch?v=example2",
        "https://www.youtube.com/watch?v=3XbtEX3jUv4",
        "https://www.youtube.com/watch?v=EiDXQmOQ6_o",

    ]

    if not video_urls:
        print("Please add YouTube video URLs to the video_urls list in the script.")
        print("\nExample:")
        print('video_urls = [')
        print('    "https://www.youtube.com/watch?v=example1",')
        print('    "https://www.youtube.com/watch?v=example2",')
        print(']')
    else:
        generate_strategy_from_videos(video_urls)

