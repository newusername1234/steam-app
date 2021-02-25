import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import db

sql = ("SELECT Game.name, Playtime.playtime_forever, Playtime.playtime_2weeks "
        "FROM Playtime JOIN Game ON Game.appid=Playtime.appid "
        f"WHERE steamid={db.search_id};")

df = pd.read_sql_query(sql, db.conn)
pd.set_option('display.max_rows', df.shape[0]) # display all df rows
df.set_index('name', inplace=True)

# set playtime columns to hrs instead of mins
df['playtime_forever'] = round(df['playtime_forever'] / 60, 2)
df['playtime_2weeks'] = round(df['playtime_2weeks'] / 60, 2)

# sort by most recent playtimes first, then by lifetime
df.sort_values(['playtime_2weeks', 'playtime_forever'], 
                ascending=False, inplace=True)

# visualize results
print(df)
playtime_2weeks = df[df['playtime_2weeks']!=0.00]['playtime_2weeks']
plt.style.use('ggplot')
x = playtime_2weeks.index[::-1]
y = playtime_2weeks.values[::-1]

x_pos = [i for i, _ in enumerate(x)]

plt.bar(x_pos, y, color='green')
plt.xlabel("Game")
plt.ylabel("Hours Played")
plt.title("Last Two Weeks Play Time")

plt.xticks(x_pos, x, rotation='vertical')

plt.show()