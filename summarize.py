from crewai import Crew, Agent, Task, Process
from crewai.project import CrewBase, agent, crew, task
from functools import cache
from langchain_groq import ChatGroq
import groq
from loguru import logger
from yt_api import list_video_ids, get_vido_transcript
from youtube_transcript_api._errors import TranscriptsDisabled
import tempfile
import webbrowser

from config.settings import config

llm = ChatGroq(temperature=0, model="llama3-70b-8192")


def get_transcripts(max_len: int = config.max_transcript_len):
    video_ids = list_video_ids()
    logger.debug(f"Found {len(video_ids)} videos")
    res = []
    for video_id in video_ids:
        logger.debug(f"Getting transcript for video {video_id}")
        try:
            res.append((video_id, get_vido_transcript(video_id)[:max_len]))
        except TranscriptsDisabled as e:
            logger.error(f"Transcripts are disabled for video {video_id}")
            continue
    return res


@CrewBase
class YTSummarizers:
    """A crew to generat summaries of YouTube videos in html."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self):
        self.llm = llm

    @agent
    def analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config["youtube_analyzer"],
            llm=self.llm,
        )

    @agent
    def frontend_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_writer"],
            llm=self.llm,
        )

    @cache
    @task
    def youtube_summary(self) -> Task:
        return Task(
            config=self.tasks_config["youtube_summary"],
            agent=self.analyzer(),
        )

    @cache
    @task
    def generate_frontend(self) -> Task:
        return Task(
            config=self.tasks_config["html_rendering"],
            agent=self.frontend_writer(),
            context=[self.youtube_summary()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=2,
            full_output=True,
        )


def kick_off_crew(crew, video_id, transcript):
    return crew.kickoff(
        inputs={
            "video_id": video_id,
            "video_transcript": transcript,
        }
    )


if __name__ == "__main__":
    tmp = tempfile.NamedTemporaryFile(delete=False)
    path = tmp.name + ".html"
    logger.info(f"Output file: {path}")
    temp_file = open(path, "a")
    with open("index.html") as f:
        temp_file.write(f.read())

    for video_id, transcript in get_transcripts():
        logger.debug(f"Processing video {video_id}")
        crew = YTSummarizers().crew()
        try:
            result = kick_off_crew(crew, video_id, transcript)
        except groq.RateLimitError as rate_limit_error:
            logger.error("Rate limit reached. Exiting")
            import time

            logger.debug("Sleeping for 60 seconds")
            time.sleep(60)
            result = kick_off_crew(crew, video_id, transcript)
        print(result)
        temp_file.write(result["final_output"])

    temp_file.write("""</main></body></html>""")
    temp_file.close()
    webbrowser.open("file://" + path)
