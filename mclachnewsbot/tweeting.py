import tweepy
from mclachnewsbot.config import parse_config

from io import BytesIO
from typing import List, Tuple
import dataclasses


@dataclasses.dataclass(frozen=True, init=True)
class Tweet:
    msg: str
    images: List[BytesIO]


def get_api_new(team: str) -> Tuple[tweepy.API, tweepy.Client]:
    config_dictionary = parse_config()
    team_config = config_dictionary["settings"][team]

    new_twitter_aut_keys = {
        "api_key": team_config["twitter_api"]["api_key"],
        "api_secret": team_config["twitter_api"]["api_key_secret"],
        "bearer_token": team_config["twitter_api"]["bearer_token"],
        "access_token": team_config["twitter_api"]["access_token"],
        "access_token_secret": team_config["twitter_api"]["access_token_secret"],
    }

    auth = tweepy.OAuthHandler(
        new_twitter_aut_keys["api_key"], new_twitter_aut_keys["api_secret"]
    )
    auth.set_access_token(
        new_twitter_aut_keys["access_token"],
        new_twitter_aut_keys["access_token_secret"],
    )
    api1 = tweepy.API(auth)
    api2 = tweepy.Client(
        bearer_token=new_twitter_aut_keys["bearer_token"],
        access_token=new_twitter_aut_keys["access_token"],
        access_token_secret=new_twitter_aut_keys["access_token_secret"],
        consumer_key=new_twitter_aut_keys["api_key"],
        consumer_secret=new_twitter_aut_keys["api_secret"],
    )
    return api1, api2


def send_tweet(text: str, team: str):
    api1, api2 = get_api_new(team)

    api2.create_tweet(text=text)
    # api1.update_status(text)
