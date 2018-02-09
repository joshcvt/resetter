# resetter

(c) 2016-17 J. W. Crockett, Jr.<sup><a href="#footnote1">1</a></sup>, [@joshcvt](http://twitter.com/joshcvt)

**resetter** is a lightweight Python 2.7 Slack bot to fetch game statuses and results.  Originally built for Major League Baseball, requesting the targeted team's status from the MLB.com API, it now can also scrape NCAA football statuses from NCAA.com and NHL scores from NHL.com.  It's built using the [Chalice](https://github.com/aws/chalice) framework.  The MLB module borrows everything significant for connecting to MLB from [natinal](https://github.com/joshcvt/natinal), though much of it is revised from the original natinal_bot form; the NCAA module is new.

The code is licensed under the MIT License.  The data belongs to MLB and the NCAA.<sup><a href="#footnote1">1</a></sup>

To use this, set up your AWS account properly for CLI work and install Chalice, then clone this repo.  You may want to adjust the default team in `app.py` unless you're Washington Nationals fans like the people in the Slack where this was originally deployed.  **chalice deploy** and note the API Gateway URL.  Then set up a Slash Command custom integration for your Slack team, paste in the API Gateway URL that Chalice gave you, set it as a GET request (not POST), and configure everything else at your leisure.

----
<a name="footnote1"/><sup>1</sup> The developer of this application claims no rights to or control over the league/association data sources it targets or the data contained within. Users of this application are themselves solely responsible for assuring that their use of this application, the sources and the data contained within complies with any and all terms and conditions set by the owners of the data sources.