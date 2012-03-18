#!/usr/bin/env python
# This script calculates podcast timestamps in IRC logs written by 
# irclog2html.py (by Marius Gedminas, see http://mg.pov.lt/irclog2html/) 
# relative to a given start and duration. It finally inserts them 
# into the given HTML logs.
#
# Copyright (C) 2011 Bastian S.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lxml import etree
from datetime import datetime, timedelta
import StringIO
import time
import sys

# symbols identifying preshow, show and postshow IRC logs
preShowSymbol = "-"
showSymbol = " "
postShowSymbol = "+"


# function calculating the podcast timestamp from IRC timestamp
def generatePlayTime(timestamp, startTime, endTime):
	global showStatus, preShowSymbol, showSymbol, postShowSymbol

	# preshow
	if timestamp < startTime and showStatus == "preshow":
		timestamp = startTime - timestamp - timedelta(hours=1)
		timestamp = datetime.fromtimestamp(timestamp.seconds)
		symbol = preShowSymbol

		# cut everything off 1 hour before show started
		if timestamp.hour >= 1:
			return None

	# postshow
	elif (timestamp > endTime and showStatus == "show") or showStatus == "postshow":
		laststamp = timestamp
		timestamp = timestamp - timedelta(hours=startTime.hour, minutes=startTime.minute)
		symbol = postShowSymbol

		# entering postshow
		if showStatus == "show":
			symbol = showSymbol

		showStatus = "postshow"

		# cut everything off 1 hour after show stopped
		if (startTime.hour + timestamp.hour == endTime.hour + 1 and (startTime.minute + timestamp.minute) % 60 > endTime.minute) or startTime.hour + timestamp.hour > endTime.hour + 1:
			return None

	# show
	elif timestamp >= startTime:
		laststamp = timestamp
		timestamp = timestamp - timedelta(hours=startTime.hour, minutes=startTime.minute)
		symbol = showSymbol

		# entering show
		if showStatus == "preshow":
			symbol = showSymbol
	
		showStatus = "show"

	else:
		print "Could not calculate podcast timestamps prior to \"%s\". Timestamps are ambigous." % timestamp.strftime("%H:%M")
		quit()

	return "%s%s" % (symbol, timestamp.strftime("%H:%M"))




if len(sys.argv) <= 3:
	# print usage information
	print "Usage: %s [HTML LOG FILE] [START TIME HH:MM] [DURATION HH:MM]" % sys.argv[0]

else:
	# we use utf-8 to avoid encoding fuckups
	reload(sys)
	sys.setdefaultencoding("utf-8")

	# retrieve log file, start/duration timestamps from commandline arguments
	filename = sys.argv[1]
	startTime = sys.argv[2]
	duration = sys.argv[3]

	# convert start/duration time
	startTime = time.strptime(startTime, "%H:%M")
	duration = time.strptime(duration, "%H:%M")

	# use a random static date to calculate podcast timestamp
	startTime = datetime(2000, 1, 1, startTime.tm_hour, startTime.tm_min)
	endTime = startTime + timedelta(hours=duration.tm_hour, minutes=duration.tm_min)

	# set initial show status
	showStatus = "preshow"

	# open html log file
	logFile = open(filename)
	log = logFile.read()
	logFile.close()

	# parse XHTML-source
	parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
	tree = etree.parse(StringIO.StringIO(log), parser)

	# XPath to log rows
	lines = tree.xpath("//table[@class='irclog']/tr")

	# check if XPath points to something
	if len(lines) == 0:
		print "Error: You can run this script only once per logfile."
	else:
		# beginning of time ;)
		lastStamp = datetime(1970, 1, 1, 0, 1)

		# loop through log rows
		for line in lines:
			if "id" in line.attrib:
				# get time from table row (tr) id (using a random static date to calculate podcast timestamp)
				timestamp = time.strptime(line.attrib["id"], "t%H:%M")
				timestamp = datetime(2000, 1, 1, timestamp.tm_hour, timestamp.tm_min)

				# running over midnight?
				if timestamp < lastStamp:
					timestamp = datetime(timestamp.year, timestamp.month, timestamp.day + 1, timestamp.hour, timestamp.minute)

				# remember last timestamp
				lastStamp = timestamp

				playTime = generatePlayTime(timestamp, startTime, endTime)

				if playTime:
					# create podcast timestamp column
					timestampTd = etree.Element("td")
					timestampTd.text = generatePlayTime(timestamp, startTime, endTime)
					timestampTd.set("class", "timestamp")

					# insert podcast timestamp as first child of table row (tr)
					line.insert(0, timestampTd)

				else:
					line.getparent().remove(line)

			elif len(list(line)) > 0 and list(line)[0].get("class") == "servermsg":
				list(line)[0].getparent().remove(list(line)[0])
				



		# write changes to file
		tree.write(filename, encoding="utf-8", pretty_print=True)

