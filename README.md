# resetter

(c) 2016-17 J. W. Crockett, Jr.<sup><a href="#footnote1">1</a></sup>, [@joshcvt](http://twitter.com/joshcvt)

**resetter** is a lightweight Python 2.7 Slack bot that responds to a slash command by getting the current status of the referenced Major League Baseball team's game or games today from the MLB.com API and posting it to the current channel.  It's built using the [Chalice](https://github.com/aws/chalice) framework and borrows everything significant for connecting to MLB from [natinal](https://github.com/joshcvt/natinal), though much of it is revised from the original natinal_bot form.

The code is licensed under the MIT License.  The data belongs to MLB.<sup><a href="#footnote1">1</a></sup>

To use this, set up your AWS account properly for CLI work and install Chalice, then clone this repo.  You may want to adjust the default MLB team in `app.py` unless you're Nats fans like us.  **chalice deploy** and note the API Gateway URL.  Then set up a Slash Command custom integration for your Slack team, paste in the API Gateway URL that Chalice gave you, set it as a GET request (not POST), and configure everything else at your leisure.

----
<a name="footnote1"/><sup>1</sup> Please note http://gdx.mlb.com/components/copyright.txt, which covers the data sources owned by MLB Advanced Media, L.P. ("MLBAM") that this application consumes. The developer of this application claims no rights to or control over these sources or the data contained within. Users of this application are themselves solely responsible for assuring that their use of this application, the sources and the data contained within complies with any and all terms and conditions set by MLBAM.