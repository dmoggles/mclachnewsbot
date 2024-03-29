# mclachnewsbot

This is a [Dagster](https://dagster.io/) project scaffolded with [`dagster project scaffold`](https://docs.dagster.io/getting-started/create-new-project).

## Getting started

First, install your Dagster code location as a Python package. By using the --editable flag, pip will install your Python package in ["editable mode"](https://pip.pypa.io/en/latest/topics/local-project-installs/#editable-installs) so that as you develop, local code changes will automatically apply.

```bash
pip install -e ".[dev]"
```

Then, start the Dagster UI web server:

```bash
dagster dev
```

Open http://localhost:3000 with your browser to see the project.


## Development

### Adding new Python dependencies

You can specify new Python dependencies in `setup.py`.

### Schedules and sensors

If you want to enable Dagster [Schedules](https://docs.dagster.io/concepts/partitions-schedules-sensors/schedules) or [Sensors](https://docs.dagster.io/concepts/partitions-schedules-sensors/sensors) for your jobs, the [Dagster Daemon](https://docs.dagster.io/deployment/dagster-daemon) process must be running. This is done automatically when you run `dagster dev`.

Once your Dagster Daemon is running, you can start turning on schedules and sensors for your jobs.

## Deploy on Dagster Cloud

The easiest way to deploy your Dagster project is to use Dagster Cloud.

Check out the [Dagster Cloud Documentation](https://docs.dagster.cloud) to learn more.


## Basic Operation
McLachNewsBot operates using the following basic loop
1. Fetch the latest news from Google News using GoogleNews API
2. Filter the news to only include these from specified sources
3. Check if we already have the metadata for this news article stored or if we had already posted it.  If not, add it to the metadata file
4. Generate a tweet from the news article using openai's gpt-3.5-turbo-0125 model.
5. Optionally, use NLP similarity assessment to filter out articles that are too similar to previously posted articles
6. Attempt to post the top article in the queue of articles that have not been posted yet.  If successful, mark as having been posted, but keep around to filter out similar articles in the future.

## Configuration
The bot is configured using a configuration file, `config.yaml`.  This file needs to have the following structure:
```
settings:
  chelsea:
    name: Chelsea FC
    language: en
    staleness: 3h
    news_search_string: chelsea fc
    nlp_filter_score: 0.975
    acceptable_news_sources:
      - Goal.com
      - Metro.co.uk
      - Evening Standard
      - The Independent
      - The Guardian
      - BBC Sport
      - Chelsea FC
      - We Ain't Got No History
      - Football.London
      - The Athletic
    verified_news_sources:
      - Chelsea FC
      - We Ain't Got No History
    twitter_api:
      client_id: **client_id**
      client_secret: **client_secret**
      api_key: **api_key**
      api_key_secret: **api_key_secret**
      bearer_token: **bearer_token**
      access_token: **access_token**
      access_token_secret: **access_token_secret**
openai_api_key: **openai_api_key**
```
The `settings` section contains the configuration for each news source that the bot is configured to monitor.  The `chelsea` section is an example of a news source configuration.  The `name` field is the name of the news source.  The `language` field is the language of the news source.  The `staleness` field is the maximum age of the news article that the bot will consider.  The `news_search_string` field is the search string that the bot will use to search for news articles.  The `nlp_filter_score` field is the minimum similarity score that the bot will use to filter out articles that are too similar to previously posted articles.  The `acceptable_news_sources` field is a list of news sources that the bot will consider.  The `verified_news_sources` field is a list of news sources that the bot will consider to be verified sources and will post regardless of any relevancy checks (though it will still conduct similarity checks).  The `twitter_api` section contains the configuration for the Twitter API.  The `openai_api_key` field is the API key for the OpenAI API.

## Configuring the NLP similarity model
In order to run the NLP similarity check, you need to download the `GoogleNews-vectors-negative300.bin` Word2Vec model file.  Because the file is quite large (3gb), I'm not including it with the repo, but it can be downloaded from [kaggle](https://www.kaggle.com/datasets/leadbest/googlenewsvectorsnegative300).  Once you have downloaded the file, you need to place it in the `models` directory.  Alternatively, you can just delete the `nlp_filter_score` field from the configuration file and the bot will not run the NLP similarity check.

## Configuring the Twitter API
In order to post tweets, you need to have a Twitter Developer account and create a new project.  Once you have created a project, you need to generate the following keys:
- API key
- API key secret
- Bearer token
- Access token
- Access token secret

An incredibly crappy documentation of it can be found [here](https://developer.twitter.com/en/docs/twitter-api).  Elon Musk is a moron and thus the twitter free tier is limited to 50 tweets per day, a limit you'll almost certainly run against.  Good luck!

## Configuring the OpenAI API
You'll need to create a openapi account and generate an API key.  Pretty good documentation is available [here](https://platform.openai.com/docs/overview).  API access to the model used is priced at less than $0.001 for a typical request this bot makes at the time of writing, so while running this will cost you money, the amount is pretty negligible.