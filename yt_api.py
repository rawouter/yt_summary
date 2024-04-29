import os
import datetime
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from youtube_transcript_api import YouTubeTranscriptApi

from config.settings import config

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]


def list_video_ids(days_backward: int = config.days_backward):
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = config.google_api_secret

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes
    )
    credentials = flow.run_local_server()

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials
    )

    request = youtube.subscriptions().list(maxResults=100, mine=True, part="snippet")
    response = request.execute()

    video_ids = []
    for item in response["items"]:
        channelId = item["snippet"]["resourceId"]["channelId"]
        request = youtube.channels().list(part="contentDetails", id=channelId)
        response = request.execute()

        uploadId = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        request = youtube.playlistItems().list(
            part="snippet", playlistId=uploadId, maxResults=3
        )
        for item in request.execute()["items"]:
            date = item["snippet"]["publishedAt"]
            if datetime.datetime.fromisoformat(date).replace(
                tzinfo=None
            ) > datetime.datetime.now() - datetime.timedelta(days=days_backward):
                video_ids.append(item["snippet"]["resourceId"]["videoId"])

    return video_ids


def get_vido_transcript(video_id):
    transcript = YouTubeTranscriptApi.get_transcript(
        video_id, languages=config.languages
    )
    return " ".join([line["text"] for line in transcript])


def main():
    video_ids = list_video_ids()
    for video_id in video_ids:
        print("=" * 80)
        print(get_vido_transcript(video_id))
        print(video_id)


if __name__ == "__main__":
    main()
