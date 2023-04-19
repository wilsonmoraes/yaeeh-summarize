from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from flask import Flask, request, jsonify

from urllib.parse import urlparse
from urllib.parse import parse_qs

import textwrap
import re
import openai

OPENAI_API_KEY = "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"
OPENAI_ORGANIZATION = "org-hdnbzGyFPauPuAOCrcVrsVCS"
PROMPT_STRING = "Write a detailed summary of the following:\n\n<<SUMMARY>>\n"

app = Flask(__name__)


@app.route("/")
def home():
    return "Hello World!"


@app.route('/summarize/', methods=['GET'])
def respond():
    # Retrieve the name from the url parameter /getmsg/?name=
    url = request.args.get("url", None)
    parsed_url = urlparse(url)
    video_id = parse_qs(parsed_url.query)['v'][0]

    openai.organization = OPENAI_ORGANIZATION
    openai.api_key = OPENAI_API_KEY

    openai.Model.list()

    # Get transcript for given YouTube video id

    transcript = YouTubeTranscriptApi.get_transcript(video_id=video_id, languages=['en', 'pt'],
                                                     preserve_formatting=True)

    # Format transcript using TextFormatter from youtube_transcript_api library
    formatter = TextFormatter()
    transcript = formatter.format_transcript(transcript)

    video_length = len(transcript)

    # If the video is ~25 minutes or more, double the chunk size
    # This is done to reduce overall amount of API calls
    chunk_size = 4000 if video_length >= 25000 else 2000

    # Wrap the transcript in chunks of characters
    chunks = textwrap.wrap(transcript, chunk_size)

    summaries = list()

    # For each chunk of characters, generate a summary
    for chunk in chunks:
        prompt = PROMPT_STRING.replace("<<SUMMARY>>", chunk)

        # Generate summary using GPT-3
        # If the davinci model is incurring too much cost,
        # the text-curie-001 model may be used in its place.
        response = openai.Completion.create(
            model="text-davinci-003", prompt=prompt, max_tokens=256
        )
        summary = re.sub("\s+", " ", response.choices[0].text.strip())
        summaries.append(summary)

    # Join the chunk summaries into one string
    chunk_summaries = " ".join(summaries)
    prompt = PROMPT_STRING.replace("<<SUMMARY>>", chunk_summaries)

    # Generate a final summary from the chunk summaries
    response = openai.Completion.create(
        model="text-davinci-003", prompt=prompt, max_tokens=2056
    )
    final_summary = re.sub("\s+", " ", response.choices[0].text.strip())

    # Print out all of the summaries
    # for idx, summary in enumerate(summaries):
    #    print(f"({idx}) - {summary}\n")

    json_resp = {'final_summary': final_summary}

    # Return the response in json format
    return jsonify(json_resp)


if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
