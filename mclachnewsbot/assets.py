from dagster import asset, Config, AssetExecutionContext
from mclachnewsbot.config import parse_config
from typing import List, Dict, Any
import GoogleNews
import requests
from bs4 import BeautifulSoup
import os
import datetime as dt
import json
import hashlib
from openai import OpenAI
from mclachnewsbot.tweeting import send_tweet

from unidecode import unidecode
import codecs
from mclachnewsbot.nlp import initialize_model, vectorize_text, similarity


class AssetConfig(Config):
    topic_name: str


def get_full_story_text(url: str) -> str:
    """
    Get the full text of a news story given the url
    """
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to get full story text for url: {url}")
    text = unidecode(codecs.decode(response.text, "unicode_escape"))
    soup = BeautifulSoup(text, "html.parser")
    # find all paragraphs that are below a header
    paragraphs = soup.find_all("p")
    full_text = " ".join([p.get_text() for p in paragraphs])
    return full_text


def load_existing_news_stories() -> List[Dict[str, Any]]:
    """
    Load existing news stories from the news directory
    """
    os.makedirs("news", exist_ok=True)
    stories = []
    if os.path.exists(f"news/news_{dt.date.today().strftime('%Y%m%d')}.json"):
        with open(f"news/news_{dt.date.today().strftime('%Y%m%d')}.json", "r") as f:
            try:
                stories = json.load(f)
            except json.JSONDecodeError:
                stories = []
    # load stories from yesterday to handle smooth daily transition
    if os.path.exists(
        f"news/news_{(dt.date.today()-dt.timedelta(days=1)).strftime('%Y%m%d')}.json"
    ):

        with open(
            f"news/news_{(dt.date.today()-dt.timedelta(days=1)).strftime('%Y%m%d')}.json",
            "r",
        ) as f:
            try:
                stories2 = json.load(f)
            except json.JSONDecodeError:
                stories2 = []
        for s in stories2:
            if s["hash"] not in [s["hash"] for s in stories]:
                stories.append(s)

    # remove any stories older than 25 hours so we don't keep propagating stale stories
    # from day to day
    stories = [
        s
        for s in stories
        if dt.datetime.strptime(s["datetime"], "%Y-%m-%d %H:%M:%S")
        > dt.datetime.now() - dt.timedelta(hours=25)
    ]
    # and lets delete the file from two days ago
    if os.path.exists(
        f"news/news_{(dt.date.today()-dt.timedelta(days=2)).strftime('%Y%m%d')}.json"
    ):
        os.remove(
            f"news/news_{(dt.date.today()-dt.timedelta(days=2)).strftime('%Y%m%d')}.json"
        )
    return stories


def create_openai_summary(full_text: str, reporter: str) -> str:
    """
    Create a summary of a news story using OpenAI
    """

    config_dictionary = parse_config()
    openai_key = config_dictionary["openai_api_key"]
    client = OpenAI(api_key=openai_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # or another model name
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Create a tweet summarising the following article. Make the summary be no more than 240 characters. Do not include any @ usernames, but do include hashtags.  Use plain text only.  Don't include any metadata such as 'Details: [URL]': "
                + full_text,
            },
        ],
    )
    summary = response.choices[0].message.content
    if len(summary) > 240:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Create a tweet summarising the following article.  Make the summary be no more than 240 characters. Do not include any @ usernames, but do include hashtags.  Use plain text only.  Don't include any metadata such as 'Details: [URL]': "
                + full_text,
            },
            {
                "role": "system",
                "content": "The summary is too long.  Please try again.",
            },
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=messages  # or another model name
        )
        summary = response.choices[0].message.content

    if "[URL]" in summary:
        # strip the entire sentense that contains that
        index_url = summary.index("[URL]")
        index_start = summary.rfind(".", 0, index_url)
        index_end = index_url + len("[URL]")
        summary = summary[:index_start] + summary[index_end:]
    if summary.startswith('"') and summary.endswith('"'):
        summary = summary[1:-1]

    # place byline before the first hashtag
    if reporter:
        if "#" in summary:
            index_hashtag = summary.index("#")
            summary = (
                summary[:index_hashtag] + f"by {reporter}. " + summary[index_hashtag:]
            )

    return summary


def get_stories_from_google_news(config: Dict[str, Any]):
    googlenews = GoogleNews.GoogleNews()
    googlenews.set_lang(config["language"])
    staleness_setting = config.get("staleness", "24h")
    googlenews.set_period(staleness_setting)
    googlenews.get_news(config["news_search_string"])

    results = googlenews.results()
    return results


def verify_story_summary(story: Dict[str, Any]) -> bool:
    """
    Verify that a story is valid
    """
    return (
        story["verified"] or story["topic_name"] in story["summary"].lower()
    ) and not story.get("expired", False)


@asset
def get_news_stories(context: AssetExecutionContext, config: AssetConfig):
    config_dictionary = parse_config()
    topic_config = config_dictionary["settings"][config.topic_name]
    context.log.info(
        f"Get news stories for {config.topic_name}" f" with settings: {topic_config}"
    )

    results = get_stories_from_google_news(topic_config)

    filtered_results = [
        r for r in results if r["media"] in topic_config["acceptable_news_sources"]
    ]

    unfiltered_results = [
        r for r in results if r["media"] not in topic_config["acceptable_news_sources"]
    ]
    context.log.info(
        f"Filtered out {len(unfiltered_results)} results from unacceptable sources"
    )

    for r in unfiltered_results:
        context.log.info(f"Unacceptable result: {r['title']}.  Source: {r['media']}")

    existing_stories = load_existing_news_stories()
    npl_model = None
    if filtered_results and "nlp_filter_score" in topic_config:

        context.log.info("Using NLP filter. Loading the model.")
        # process stories using nlp similarity measure
        npl_model = initialize_model("models/GoogleNews-vectors-negative300.bin")

    # get full text for each story
    for r in filtered_results:
        context.log.info(f"Acceptable result: {r['title']}.  Source: {r['media']}")
        context.log.info(f"Full metadata: {r}")
        r["full_text"] = get_full_story_text("http://" + r["link"])
        r["hash"] = hashlib.md5(r["link"].encode()).hexdigest()
        r["processed"] = False
        r["datetime"] = (
            r["datetime"].strftime("%Y-%m-%d %H:%M:%S")
            if r["datetime"]
            else dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        r["topic_name"] = config.topic_name
        r["can_be_tweeted"] = True
        r["has_been_tweeted"] = False
        r["verified"] = r["media"] in topic_config["verified_news_sources"]
        # r['expired']=False
        if npl_model:
            r["nlp_vector"] = vectorize_text(r["full_text"], npl_model)
        else:
            r["nlp_vector"] = None

    for r in filtered_results:
        if r["hash"] in [s["hash"] for s in existing_stories]:
            context.log.info(f"Story {r['title']} already exists.  Skipping")
            continue
        existing_stories.append(r)

    # mark stories as expired if they are older than the staleness setting.  Not going to publish these
    staleness_setting = topic_config.get("staleness", "24h")
    context.log.info(f"Found {len(filtered_results)} new stories")
    context.log.info(f"Total stories: {len(existing_stories)}")

    context.log.info(f"Removing stales with staleness setting of {staleness_setting}")

    for s in existing_stories:
        if s["datetime"]:
            datetime = dt.datetime.strptime(s["datetime"], "%Y-%m-%d %H:%M:%S")
            if dt.datetime.now() - datetime > dt.timedelta(
                hours=int(staleness_setting.split("h")[0])
            ):
                s["can_be_tweeted"] = False
                context.log.info(
                    f"Story {s['title']} is stale.  Setting can_be_tweeted to False"
                )
    os.makedirs("news", exist_ok=True)
    with open(f'news/news_{dt.date.today().strftime("%Y%m%d")}.json', "w") as f:
        json.dump(existing_stories, f)
    return existing_stories


@asset(deps=[get_news_stories])
def create_news_summary(context: AssetExecutionContext):
    stories = load_existing_news_stories()
    unprocessed_stories = [s for s in stories if not s["processed"]]
    for s in unprocessed_stories:
        context.log.info(f"Processing story: {s['title']}")
        s["summary"] = create_openai_summary(s["full_text"], s.get("reporter", ""))

        s["processed"] = True

    with open(f'news/news_{dt.date.today().strftime("%Y%m%d")}.json', "w") as f:
        json.dump(stories, f)
    return stories


@asset(deps=[create_news_summary])
def tweet_stories(context: AssetExecutionContext):
    config = parse_config()
    stories = load_existing_news_stories()
    if len(stories) == 0:
        context.log.info("No stories to tweet")
        return []
    topic_settings = config["settings"][stories[0]["topic_name"]]

    # kind of a wierd place to do nlp filter, but can't think of a better one
    for i, s1 in enumerate(stories):
        for j, s2 in enumerate(stories):
            if not s1 or not s2:
                continue
            if i == j:
                continue
            similarity_score = similarity(s1["nlp_vector"], s2["nlp_vector"])
            if (
                similarity_score > topic_settings["nlp_filter_score"]
                and s2["has_been_tweeted"]
            ):  # don't tweet the same story twice
                s1["can_be_tweeted"] = False

                context.log.info(
                    f"Story {s1['title']} and {s2['title']} have similar content with a score of {similarity_score}.  Indexes: {i},{j}.  Setting can_be_tweeted to False"
                )

    unprocessed_stories = [
        s
        for s in stories
        if s["can_be_tweeted"] and not s["has_been_tweeted"] and verify_story_summary(s)
    ]
    # tweet the first story that hasn't been tweeted
    for s in unprocessed_stories:
        context.log.info(f"Tweeting story: {s['title']}")
        context.log.info(f"Summary: {s['summary']+ ' ' + s['link']}")
        try:
            # who knows what's in the summary, just use the title
            if s["topic_name"] not in s["summary"].lower():
                if s["verified"] != True:
                    context.log.info(
                        f"Story {s['title']} not tweeted because topic name not in summary"
                    )
                    continue
                s["summary"] = s["title"]
            send_tweet(s["summary"] + " " + s["link"], s["topic_name"])
            s["has_been_tweeted"] = True
        except Exception as e:
            context.log.error(f"Error tweeting story: {s['title']}.  Error: {e}")
            if "Tweet text is too long" in str(e):
                s["has_been_tweeted"] = False
                s["processed"] = False
        finally:
            if s["has_been_tweeted"]:
                context.log.info(f"Tweeted story: {s['title']}")
                break

    with open(f'news/news_{dt.date.today().strftime("%Y%m%d")}.json', "w") as f:
        json.dump(stories, f)
    return stories
