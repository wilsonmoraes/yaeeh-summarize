import re
import textwrap
from time import time, sleep
from urllib.parse import parse_qs
from urllib.parse import urlparse

import openai
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

OPENAI_API_KEY = "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"
OPENAI_ORGANIZATION = "org-hdnbzGyFPauPuAOCrcVrsVCS"
PROMPT_STRING = "Escreva um resumo detalhado do seguinte vídeo:\n\n<<SUMMARY>>\n"
openai.organization = OPENAI_ORGANIZATION
openai.api_key = OPENAI_API_KEY

openai.Model.list()

app = Flask(__name__)


@app.route("/")
def home():
    return "Hello World!"


@app.route('/summarize/', methods=['GET'])
def respond():
    # Retrieve the name from the url parameter /getmsg/?name=
    url = request.args.get("url", None)
    # Download transcript
    video_id, text = get_transcript(url)
    json_resp = {}

    # Summarize the transcript (chunk by chunk if needed)
    if text:
        # Summarize transcript
        results = ask_gpt(text, 'SUMMARY')
        json_resp['summary'] = '\n\n'.join(results)

    # Return the response in json format
    return jsonify(json_resp)


def get_transcript(url):
    url_data = urlparse(url)
    video_id = parse_qs(url_data.query)["v"][0]
    if not video_id:
        print('Video ID not found.')
        return None

    try:
        formatter = TextFormatter()

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'pt'])
        text = formatter.format_transcript(transcript)
        text = re.sub('\s+', ' ', text).replace('--', '')
        return video_id, text

    except Exception as e:
        print('Error downloading transcript:', e)
        return None


def gpt3_completion(prompt, tokens=500):
    max_retry = 3
    retry = 0
    while True:
        try:
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=prompt,
                max_tokens=tokens)
            text = response.choices[0].text.strip()
            text = re.sub('\s+', ' ', text)
            return text

        except Exception as e:
            retry += 1
            if retry >= max_retry:
                return "GPT3 error: %s" % e
            print('Error communicating with OpenAI:', e)
            sleep(1)


def ask_gpt(text, job='SUMMARY'):
    # Summarize chunks
    chunks = textwrap.wrap(text, width=10000)
    results = list()
    for i, chunk in enumerate(chunks):
        prompt = PROMPT_STRING.replace('<<SUMMARY>>', chunk)
        prompt = prompt.encode(encoding='ASCII', errors='ignore').decode()
        output = ''
        if job == 'SUMMARY':
            output = gpt3_completion(prompt, tokens=500)
        elif job == 'REWRITE':
            output = gpt3_completion(prompt, tokens=2048)
        results.append(output)
        print(f'{i + 1} of {len(chunks)}\n{output}\n\n\n')

    return results


if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
