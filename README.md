# resetter

(c) 2016-26 J. W. Crockett, Jr., [@joshcvt.on29.net](https://bsky.app/profile/joshcvt.on29.net)

**resetter** is a Python 3.11 bot, built with [Chalice](https://github.com/aws/chalice) on AWS Lambda, that fetches game statuses and results. It covers MLB (via StatsAPI), the NHL (via the NHLE API), and MLS and college football (via ESPN's site API). It can:

* answer a Slack slash command (`/reset WSH`, `/reset nhl 2024-4-1`, ...) with a team's or league's games,
* post a scoreboard to Slack on a schedule, through a webhook stored in SSM Parameter Store, and
* watch for a team's games to go final and post to Bluesky when they do (optionally only on wins): this is what runs [journeybot](https://bsky.app/profile/journeybot.on29.net).

The code is licensed under the MIT License.  The data belongs to its respective league/association owners and/or their licensees.<sup><a href="#footnote1" name="ref1">1</a></sup>

## Setup

* set up your AWS account properly for CLI work
* clone this repo
* create a venv or your other favorite Python working environment for Python >= 3.11
* `pip install -r requirements.txt` (which will install the Chalice CLI)
* Customize the `DEFAULT_PARAM` in `app.py` unless you're Washington Nationals fans like the people in the Slack where this was originally deployed
* Decide which of the features below you want, and set up what each one needs.
* Unless you're using only the slash command, copy `.chalice/sample-policy-dev.json` to `.chalice/policy-dev.json` and replace the placeholder account ID `123456789012` with yours. The sample policy covers everything below: the SSM parameters under `/resetter/`, the DynamoDB table, and the Lambda invoke used by the test post. If you're using only the slash command, you don't need a custom IAM policy: copy `.chalice/sample-config-no-custom-policy.json` to `.chalice/config.json`, and comment out both `@app.schedule` decorators in `app.py` (see below).
* `chalice deploy` and note the given API Gateway URL.  Then set up a Slash Command custom integration for your Slack team, paste in the API Gateway URL that Chalice gave you, set it as a GET request, and configure everything else at your leisure.

`app.py` has two scheduled functions, `scoreboardPoster` and `monitorChecker`. Schedules can't be turned off by configuration (a Chalice limitation), so *to disable either one, comment out the `@app.schedule` decorator on its function*. Both schedules are cron expressions in UTC.

### Scheduled Slack scoreboard posts

* Establish a [Slack webhook](https://api.slack.com/messaging/webhooks), get the POST URL from that, and run the Terraform in `terraform/slackkey` to store it in Parameter Store as `/resetter/slack_web_hook_url`.
* In `app.py`, check out the `SCHEDULED_POST*` lines, including the cron schedule. Adjust them as you desire or empty them out.

### Bluesky game-final monitor

`monitorChecker` runs every 5 minutes (`MONITOR_CRON_SCHEDULE`). For each monitor configured, it checks whether that team's game today has gone final, and if so posts the game's result plus your message to Bluesky. Each game is posted at most once: a record of it goes in DynamoDB.

* Run the Terraform in `terraform/ddb` to create the `resetter-game-status` DynamoDB table.
* Create a Bluesky [app password](https://bsky.app/settings/app-passwords) for the posting account and store it in Parameter Store as a SecureString named `/resetter/bsky/<handle>`, e.g. `/resetter/bsky/journeybot.on29.net`.
* Configure monitors in `.chalice/config.json` as the `MONITOR_SET_JSON` environment variable: a JSON list, as a string, of objects with these keys:

  | key | meaning |
  |---|---|
  | `sport` | `mlb`, `nhl` or `mls` |
  | `team` | team code, e.g. `WSH` |
  | `notifier` | `bsky` (the only notifier so far) |
  | `notifierUser` | the Bluesky handle to post as; its app password must be in SSM as above |
  | `message` | text appended to the game result. The first URL in the post gets a link-preview card. |
  | `winOnly` | if present (any value), post only when the team wins |
  | `test` | if present (any value), do everything except post. For local runs; see `test_monitors.py`. |

#### Test posts

To check that posting works from Lambda, set `ENABLE_TEST_POST` to `"true"` in `.chalice/config.json` and deploy, then send `/reset test-journeybot-post` from Slack. That makes a real post from the first `bsky` monitor, prefixed `[test post, please ignore]`, at most once per UTC hour. The result is in the `monitorChecker` CloudWatch logs. Set the flag back to `"false"` and redeploy when you're done: it's off for any value other than `true`, `1`, `yes` or `on`.

The slash-command endpoint doesn't verify that requests really come from Slack, so while the flag is on, anyone with the API Gateway URL can trigger a test post (within that hourly limit).

## Testing

Testing is league-by-league from your development environment against live data, mostly because the leagues change both their feed spec and some of the data included in it infuriatingly often ([varying capitalization of branded arena names](https://github.com/joshcvt/resetter/commit/3168abde08cabe0be9c979056bd485f52b90f4c4) is just the tip of the iceberg) such that static test data is of very limited use (and also actual data is all copyright the leagues, and I don't want to tempt the copyright dragons any more than necessary). The `test_mlb.py`, `test_nhl.py`, `test_mls.py` and `test_ncaaf.py` scripts fire off a varying set of requests for real and non-existent teams, generally for yesterday, today and tomorrow (so you get finished games, potentially in-progress today, and games that haven't started yet). `test_nhl_today.py` does the same for the NHL's scoreboard and team lookups, `test_global.py` tries ambiguous and cross-league names (`Toronto`, `NY`, `garbage`), and `test_dates.py` covers date-specific requests. `test_monitors.py` runs the monitor locally with `test` set, so it doesn't post. `test_slackPost.py` *does* post: it sends scheduled-style scoreboards to your real webhook, to the `backtalk` channel.

----

<a name="footnote1" href="#ref1">1.</a> The developer of this application claims no rights to or control over the league/association data sources it targets or the data contained within. Users of this application are themselves solely responsible for assuring that their use of this application, the sources and the data contained within complies with any and all terms and conditions set by the owners of the data sources.
