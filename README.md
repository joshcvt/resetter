# resetter

(c) 2016-21 J. W. Crockett, Jr.<sup><a href="#footnote1">1</a></sup>, [@joshcvt](http://twitter.com/joshcvt)

**resetter** is a lightweight Python 2.7 Slack bot to fetch game statuses and results.  Originally built for Major League Baseball, requesting the targeted team's status from the MLB.com API, it can also scrape NHL scores from NHL.com; it was previously able to scrape NCAA football statuses from NCAA.com, but [they retired the old endpoint and I haven't had the free time during college football Saturdays to rewrite it yet](https://github.com/joshcvt/resetter/issues/4).  It's built using the [Chalice](https://github.com/aws/chalice) framework.  The MLB module borrows everything significant for connecting to MLB's GDX API from [natinal](https://github.com/joshcvt/natinal), though much of it is revised from the original natinal_bot form; the NCAA and NHL modules are original.

The code is licensed under the MIT License.  The data belongs to its respective league/association owners and/or their licensees.<sup><a href="#footnote1">1</a></sup>

To use this, set up your AWS account properly for CLI work and install Chalice, then clone this repo.  You may want to adjust the default team in `app.py` unless you're Washington Nationals fans like the people in the Slack where this was originally deployed.  **chalice deploy** and note the API Gateway URL.  Then set up a Slash Command custom integration for your Slack team, paste in the API Gateway URL that Chalice gave you, set it as a GET request (not POST), and configure everything else at your leisure.

Testing is league-by-league from your development environment against live data, mostly because the leagues change both their feed spec and some of the data included in it infuriatingly often ([varying capitalization of branded arena names](https://github.com/joshcvt/resetter/commit/3168abde08cabe0be9c979056bd485f52b90f4c4) is just the tip of the iceberg) such that static data is of very limited use. The ```test_league.py``` scripts fire off a varying set of requests for real and non-existent teams, generally for yesterday, today and tomorrow (so you get finished games, potentially in-progress today, and games that haven't started yet).

----
<a name="footnote1"/><sup>1</sup> The developer of this application claims no rights to or control over the league/association data sources it targets or the data contained within. Users of this application are themselves solely responsible for assuring that their use of this application, the sources and the data contained within complies with any and all terms and conditions set by the owners of the data sources.
