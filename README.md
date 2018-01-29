# halite
This is my submission for the halite-2 coding competition

# overview
I took the approach of programming a generic RTS AI, where I broke down the components into micro-management strategies and overall macro-strategies. Macro-decisions would bring a ship close to an objective, and once it's close enough the micro-decisions would take over and decide what action that particular ship would take.

Typical workflow looks like this:
1) Get overall turn strategy - three general strategies which are Rush, Two-player and Four-player
2) Compute macro-utilites for each ship - enemy docked ships have the most utility in two-player games, and planets that are not totally colonized have the most utility in 4 player games

Loop through each ship, sorted by highest utility:
1) Micro decisions - decide to run, fight, zone-out, round or zone-in
2) Macro - if we're not close to any ship just move towards the highest utility target
