import sqlite3
import requests
from steamapikey import steam_api_key

# set up db
conn = sqlite3.connect('steam_db.sqlite')
cur = conn.cursor()
cur.executescript('''
CREATE TABLE IF NOT EXISTS User (
    steamid INTEGER NOT NULL PRIMARY KEY UNIQUE,
    personaname TEXT,
    profileurl TEXT,
    avatar TEXT,
    avatarmedium TEXT,
    avatarfull TEXT,
    avatarhash TEXT,
    last_fetched REAL
);

CREATE TABLE IF NOT EXISTS Game (
    appid INTEGER NOT NULL PRIMARY KEY UNIQUE,
    name TEXT,
    img_icon_url TEXT,
    img_logo_url TEXT
);

CREATE TABLE IF NOT EXISTS Friend (
    steamid INTEGER NOT NULL,
    friendid INTEGER NOT NULL,
    PRIMARY KEY (steamid, friendid)
);

CREATE TABLE IF NOT EXISTS Playtime (
    steamid INTEGER NOT NULL,
    appid INTEGER NOT NULL,
    playtime_forever INTEGER,
    playtime_2weeks INTEGER,
    PRIMARY KEY (steamid, appid)
);
''')

search_id = input('Steam id to search:\n')
if len(search_id) < 1:
    search_id = '76561198066486519'
cur.execute('SELECT personaname from User WHERE steamid=?', (search_id,))
try:
    print(f'fetching data for {cur.fetchone()[0]}...')
except TypeError:
    print('fetching data for new entry...')

# only fetch if they havent been fetched within the last day
cur.execute('SELECT last_fetched FROM User WHERE steamid=? AND last_fetched>julianday("now")-1', (search_id,))
if cur.fetchone() == None:
    # get ids
    res = requests.get(f'http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={steam_api_key}&steamid={search_id}&relationship=friend')
    friends = res.json()['friendslist']['friends']
    # start with own id and add ids from friend list
    steam_ids = [search_id]
    for friend in friends:
        # add friends to friend table
        cur.execute('INSERT OR IGNORE INTO Friend VALUES (?,?)', (search_id, friend['steamid']))
        steam_ids.append(str(friend['steamid']))

    # get both user and friends profile data
    res = requests.get(f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={steam_api_key}&steamids={",".join(steam_ids)}')
    user_data = res.json()['response']['players']
    # remove stuff we dont care about
    to_remove = ['communityvisibilitystate',
                'profilestate',
                'commentpermission',
                'lastlogoff',
                'personastate',
                'realname',
                'primaryclanid',
                'personastateflags',
                'timecreated',
                'loccountrycode',
                'locstatecode',
                'gameid',
                'gameserverip',
                'gameextrainfo',
                'cityid',
                'loccityid']
    for user in user_data:
        remove = []
        for key in user.keys():
            if key in to_remove:
                remove.append(key)
        [user.pop(key) for key in remove]

        steamid = user.pop('steamid')

        # update last_fetched only for search_id
        if steamid == search_id:
            cur.execute('UPDATE User SET personaname=?, profileurl=?, avatar=?, avatarmedium=?, avatarfull=?, avatarhash=?, last_fetched=julianday("now") WHERE steamid=?', tuple(x for x in user.values()) + (steamid,))
            if cur.rowcount == 0:
                cur.execute('INSERT INTO User VALUES (?,?,?,?,?,?,?,julianday("now"))', (steamid,) + tuple(x for x in user.values()))
        else:
            try:
                cur.execute('UPDATE User SET personaname=?, profileurl=?, avatar=?, avatarmedium=?, avatarfull=?, avatarhash=? WHERE steamid=?', tuple(x for x in user.values()) + (steamid,))
                if cur.rowcount == 0:
                    cur.execute('INSERT INTO User VALUES (?,?,?,?,?,?,?,NULL)', (steamid,) + tuple(x for x in user.values()))
            except:
                print(user.values())

    # get user game data
    for user_id in steam_ids:
        res = requests.get(f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={steam_api_key}&steamid={user_id}&include_appinfo=true&include_played_free_games=true')
        # try:
        if 'games' not in res.json()['response'].keys():
            game_data = res.json()['response']
        else:
            game_data = res.json()['response']['games']
            # to_remove = ['playtime_windows_forever',
            #             'playtime_mac_forever',
            #             'playtime_linux_forever',
            #             'has_community_visible_stats']
        for game in game_data:
            #     remove = []
            #     for key in game.keys():
            #         if key in to_remove:
            #             remove.append(key)
            #     [game.pop(key) for key in remove]
        
            if 'playtime_2weeks' not in game.keys():
                game['playtime_2weeks'] = 0

            cur.execute('UPDATE Playtime SET playtime_forever=?, playtime_2weeks=? WHERE steamid=? AND appid=?', (game['playtime_forever'], game['playtime_2weeks'], user_id, game['appid']))
            if cur.rowcount == 0:
                cur.execute('INSERT INTO Playtime VALUES (?,?,?,?)', (user_id, game['appid'], game['playtime_forever'], game['playtime_2weeks']))
            cur.execute('INSERT OR IGNORE INTO Game VALUES (?,?,?,?)', (game['appid'], game['name'], game['img_icon_url'], game['img_logo_url']))
    conn.commit()