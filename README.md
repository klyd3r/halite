# halite
This is my submission for the halite-2 AI programming competition (http://halite.io). My first ever project coding in Python, and I'm really thankful to have had such a fun project to work on. Special thanks to ewirkerman's BotThoughtViewer, which helped a lot in the initial debugging phases.

# background
I'm an avid gamer, having played numerous RTSes (StarCraft/C&C series/Dota) growing up and am pretty familiar with general RTS strategy and concepts. I also have some programming experience from school/work experiences, and wanted to use this as a way to write an entire project by myself and learn as much as I could along the way.

# overview
I took the approach of programming a generic RTS AI, where I broke down the components into micro-management strategies and overall macro-strategies. Macro-decisions would bring a ship close to an objective, and once it's close enough the micro-decisions would take over and decide what action that particular ship would take.

Typical workflow looks like this:
1) Get overall turn strategy - I have three general strategies which are Rush, Two-player and Four-player. My bot runs with different parameters depending on what strategy we've picked. I went with this setup because I noticed very early on that 2-player games and 4-player games are pretty different. In 2-player games the middle of the map is extremely important, in 4-player games you want to stay away from the middle until later on in the game. It also doesn't really pay to be too aggressive in 4-player games.
2) Compute macro-utilites for each ship - Each entity (enemy docked ship, enemy undocked ship, uncolonized planet) had a fixed utility, that was discounted by distance.

Loop through each ship, sorted by highest utility:
1) Micro decisions - decide to run, fight, zone-out, round or zone-in. More details of how I do these decisions in micro.py. Basically my ships run away if it might die next turn, fight if we can outnumber the enemy, wait to fight if we don't have enough to engage, etc etc.
2) Macro - if we're not close to any ship just move towards the highest utility target

# version history
I submitted really often, given that I didn't have a very robust regression testing framework and there was no real penalty for submitting frequently.

versions
1-100: Most of my macro and micro strategies were already in. I got to ~50 rank with these versions.

~200: I got to ~30 rank - by data mining my games and tweaking my rush parameters based on how many rush games I was winning vs. non-rush games

~270: I got to <20 rank - by parsing my local replays I suddenly realized that I was losing too many ships through friendly collisions. I reworked my whole navigation and my rank significantly improved.

The rest of my versions were just random minor tweaks - none of them significantly improved my bot.

# learning points
Running sims with cloud services - I should have engaged cloud computing services. My only form of regression testing was an A/B test with my previous bot, and even that took a while as 100 simulations could easily take up to half an hour. This could have drastically improved my idea generation/implementation/testing process

Using the halite API earlier - I started using the API after the start of the new year, where I had less free time. I was able to write a number of scripts to parse the leaderboard data, download replays of my games and parse through those replays for useful information, but I believe there was probably a lot more information that I could have extracted but just didn't have the time for. It did allow me to focus on the right things going into the end of the competition (improving non-rush 2 player games and navigation), so it still worked out pretty well for me.

Building more visualization, debugging tools - I would say I spent less than 3% of my time on this side project developing visualization and debugging tools. In hindsight, reading the other post mortems (expecially reCurs3's), these tools would've helped a ton.
