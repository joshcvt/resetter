#!/usr/bin/env python

ncaaNickDict = {'rebels': 'unlv', 
	'warhawks': 'la.-monroe', 'louisiana-monroe': 'la.-monroe', 
	'cougars': 'washington st.', 'wsu': 'washington st.', 'washington state': 'washington st.',
	'wolverines': 'michigan', 
	'panthers': 'pittsburgh', 'pitt': 'pittsburgh',
	'thundering herd': 'marshall', 
	'broncos': 'western mich.', 'western michigan':'western mich.', 
	'lobos': 'new mexico', 
	'golden eagles': 'southern miss', 
	'tar heels': 'north carolina', 
	'midshipmen': 'navy', 'mids': 'navy',
	'red wolves': 'arkansas st.', 'arkansas state': 'arkansas st.', 
	'orange': 'syracuse', 
	'boilermakers': 'purdue', 
	'golden hurricane': 'tulsa', 
	'cavaliers': 'virginia', 'uva':'virginia', 'hoos': 'virginia', 'wahoos':'virginia',
	'golden panthers': 'fiu', 
	'green wave': 'tulane', 
	'cardinals': 'louisville', 
	'hokies': 'virginia tech', 'vt': 'virginia tech',
	'huskies': 'washington', 
	'cornhuskers': 'nebraska', 
	'wildcats': ['Northwestern','Kentucky'], 
	'rockets': 'toledo', 
	'nittany lions': 'penn st.', 'penn state':'penn st.',
	'demon deacons': 'wake forest', 
	'gamecocks': 'south carolina', 
	'red raiders': 'texas tech', 
	'sun devils': 'arizona st.', 'arizona state': 'arizona st.', 
	'jayhawks': 'kansas', 
	'fighting illini': 'illinois', 'illini': 'illinois',
	'cowboys': 'wyoming', 
	'golden flashes': 'kent state', 
	'commodores': 'vanderbilt', 'vandy':'vanderbilt',
	"ragin' cajuns": 'louisiana', 'louisiana-lafayette':'louisiana', 
	'longhorns': 'texas', 
	'sooners': 'oklahoma', 
	'terrapins': 'maryland', 
	'chippewas': 'cent. michigan', 'central michigan':'cent. michigan',
	'chanticleers': 'coastal caro.', 'coastal carolina': 'coastal caro.',
	'razorbacks': 'arkansas', 
	'monarchs': 'old dominion', 
	'buckeyes': 'ohio st.', 'ohio state': 'ohio st.', 'tosu':'ohio st.',
	'bulls': 'south florida', 
	'black knights': 'army', 
	'knights': 'ucf', 
	'zips': 'akron', 
	'fighting irish': 'notre dame', 'irish':'notre dame',
	'horned frogs': 'tcu', 
	'rams': 'colorado state', 
	'49ers': 'charlotte', 
	'yellow jackets': 'georgia tech', 'jackets':'georgia tech',
	'badgers': 'wisconsin', 
	'buffaloes': 'colorado', 
	'golden gophers': 'minnesota', 'gophers':'minnesota',
	'redhawks': 'miami (ohio)', 'miami':'miami (fla.)', 'miami (oh)': 'miami (ohio)', 'miami ohio': 'miami (ohio)','miami-ohio': 'miami (ohio)',
	'pirates': 'east carolina', 
	'blue devils': 'duke', 
	'bears': 'baylor', 
	'eagles': 'ga. southern', 'georgia southern':'ga. southern',
	'seminoles': 'florida state', 'noles': 'florida state',
	'tigers': ['Missouri', 'Clemson', 'Auburn', 'LSU'], 'mizzou':'missouri',
	'bulldogs': ['Mississippi State','Georgia'], 'mississippi state':'mississippi st.', 'dawgs':'georgia', 
	'wolfpack': 'nc state', 'north carolina state': 'nc state', 'n.c. state': 'nc state', 
	'mountaineers': 'west virginia', 'eers': 'west virginia', 'wvu': 'west virginia',
	'hurricanes': 'miami (fla.)', 'canes': 'miami (fla.)',
	'trojans': 'usc', 
	'bearcats': 'cincinnati', 
	'utes': 'utah', 
	'roadrunners': 'utsa', 
	'bobcats': 'texas state', 
	'mustangs': 'smu', 
	'hilltoppers': 'western kentucky', 
	'aztecs': 'san diego state', 
	'beavers': 'oregon state', 
	'hawkeyes': 'iowa', 
	'wolf pack': 'nevada', 
	'crimson tide': 'alabama', 
	'cyclones': 'iowa state', 
	'ducks': 'oregon', 
	'aggies': 'texas a&m', # sorry utah state.
	'hoosiers': 'indiana', 
	'warriors': 'hawaii', 
	'scarlet knights': 'rutgers', 
	'cardinal': 'stanford', 
	'vandals': 'idaho', 
	'blue raiders': 'middle tenn.', 'middle tennessee': 'middle tenn.',
	'jaguars': 'south alabama', 
	'miners': 'utep', 
	'golden bears': 'california', 'berkeley': 'california', 'cal': 'california',
	'spartans': 'san jose state', 'sjsu':'san jose state', 
	'blazers': 'uab', 
	'gators': 'florida', 
	'owls': 'temple', 
	'bruins': 'ucla', 
	'falcons': 'bowling green', 
	'minutemen': 'massachusetts', 'umass': 'massachusetts', 
	'volunteers': 'tennessee', 'vols':'tennessee',
	'mean green': 'north texas'
}

displayOverrides = {
	'ohio st.': "Ohio State",
	'army west point': "Army",
	'miami (fla.)': "Miami",
	'penn st.': 'Penn State',
	'middle tenn.': 'Middle Tennessee',
	'arizona st.': "Arizona State",
	'western mich.': "Western Michigan",
	'cent. michigan': 'Central Michigan',
	'coastal caro.':'Coastal Carolina',
	'ga. southern':'Georgia Southern'
}
