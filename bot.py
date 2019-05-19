import discord, json, time, random, re, datetime, os, youtube_dl, asyncio, logging, dateutil.parser, subprocess, lxml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gtts import gTTS
from lxml import etree
from urllib.request import urlopen

### DEBUG MODE : ON
#logging.basicConfig(level=logging.DEBUG)

### BOT
bot = discord.Client()

#### Variables globales
version = "2.0.3"
bot_secret = ""
bot_name = ""
admin_name = ""
id_admin = ""
server_id = ""
plugdj_id = ""
#general_channel = discord.Object(id='')
#blabla_channel = discord.Object(id='')
#plugdj_channel = discord.Object(id=plugdj_id)
#channel = discord.Object(id='')

boot_text=f"""
BOOT TEXT HERE
"""

help_text=f"""
:information_source: Voici mon manuel d'utilisation :
:white_small_square: `!help wolfram` : afficher de nouveau ce manuel d'utilisation.
:white_small_square: `!play` : ajouter un lien YouTube à la playlist.
:white_small_square: `!playing` ou `!np` : consulter la piste en train d'être jouée.
:white_small_square: `!playlist` ou `!pl` : consulter la playlist.
:white_small_square: `!pp` : concaténation de `!playing` et `!playlist`.
:white_small_square: `!search` : rechercher automatiquement dans YouTube.
:white_small_square: `!searchance` : idem que `!search`, mais pour les chanceux. <:larry:344541137752555520>
:white_small_square: `!skip` : permet de passer à la piste suivante à l'issue d'un vote (avec la réaction ':thumbsup:').
:white_small_square: `!rm` : permet de retirer ses propositions de piste (exemple : `!rm 2`).

(`!search` renvoie le résultat YouTube qui me semble le plus pertinent. Cependant, vous devez le valider en ajoutant une réaction ':thumbsup:' au résultat, dans la minute qui suit son apparition. Cette validation n'est pas nécessaire si `!searchance` est invoqué à la place.)
"""

#### Notifier de l'initialisation
@bot.event
async def on_ready():
    print("Initialisation...")
    await bot.send_message(blabla_channel, boot_text)
    await bot.change_presence(game=discord.Game(name='doing nothing'))

#### Check & pass URL
@bot.event
async def check_url(url, author, channel):
    pattern = re.compile("^(https?\:\/\/)?(www\.youtube\.com|youtu\.?be)\/.+$")
    if pattern.match(url):
        youtube = etree.HTML(urlopen(url).read().decode('utf-8'))
        title = ''.join(youtube.xpath("//span[@id='eow-title']/@title"))
        await plugdj(url, title, author, channel)
    else:
        await bot.send_message(channel, f":warning: <@{author}> Musique **invalide** !")

#### Now playing
@bot.event
async def now_playing(channel):
    try:
        if plugdj.player.is_playing():
            time_player = time.strftime("%M:%S", time.gmtime(plugdj.time))
            duration = time.strftime("%M:%S", time.gmtime(plugdj.player.duration))
            piste = f":play_pause: Piste en cours : **{plugdj.titre}**.\n"
            piste += f":white_small_square: Proposée par : <@{plugdj.user}>.\n"
            piste += f":white_small_square: **{time_player}** - **{duration}**."
            await bot.send_message(channel, piste)
        else:
            await bot.send_message(channel, ":stop_button: Il n'y a **aucune piste** en cours.")
    except:
        await bot.send_message(channel, ":warning: Le player n'est pas initialisé.")

#### Display playlist/queue
@bot.event
async def show_playlist(channel):
    try:
        if plugdj.player.is_playing() and plugdj.liste != []:
            playlist = f":arrow_forward: **{len(plugdj.liste)} musique(s)** dans la playlist :\n"
            rang = 1
            for item in plugdj.liste:
                playlist += f":white_small_square: **{rang}.** {item['titre']} (<@{item['user']}>).\n"
                rang += 1
        else:
            playlist = f":arrow_forward: **Aucune musique** dans la playlist."

        await bot.send_message(channel, playlist)

    except:
        await bot.send_message(channel, ":warning: Le player n'est pas initialisé.")

#### Skip command
@bot.event
async def skip(channel, voice_channel):
    votes_skip = (len(voice_channel.voice_members) - 1)//2 +1

    if votes_skip > 1:
        msg = await bot.send_message(channel, f":fire: Je passe à la piste suivante s'il y a au moins **{votes_skip} vote(s)**.")

        res, votes, liste = "", 0, []

        while (res != None) and (votes < votes_skip):
            res = await bot.wait_for_reaction('👍', timeout=30, message=msg)
            if res != None:
                if ('{0.reaction.emoji}'.format(res) == '👍') and ('{0.user}'.format(res) not in liste): votes += 1
                if '{0.user}'.format(res) not in liste: liste.append('{0.user}'.format(res))

        if res == None: await bot.send_message(channel, ":timer: **Temps écoulé** : pas assez de votes.")

        if votes >= votes_skip:
            await bot.send_message(channel, ":track_next: Assez de votes, je passe donc à la **piste suivante**.")
            plugdj.player.stop()

    else:
        await bot.send_message(channel, ":track_next: Je passe à la **piste suivante**.")
        plugdj.player.stop()

#### Search command
@bot.event
async def search(channel, author, recherche, chance):
    await bot.send_message(channel, f':clock4: Recherche en cours pour *{recherche}*...')
    command = f'youtube-dl ytsearch:"{recherche}" --get-id --no-playlist --geo-bypass-country FR'
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
    while process.poll() == None: await asyncio.sleep(0.2)
    resultat = process.stdout.read()

    if resultat != "":
        url = f"https://www.youtube.com/watch?v={resultat}"

        if chance == True:
            await bot.send_message(channel, f":mag_right: **J'ai trouvé un résultat** pour *{recherche}*, je l'ajoute directement à la playlist.")
            await check_url(url, author.id, channel)

        else:
            msg = await bot.send_message(channel, f":mag_right: <@{author.id}> **Est-ce le résultat attendu ?** Voici ce que j'ai trouvé : {url}")
            res = await bot.wait_for_reaction('👍', user=author, timeout=60, message=msg)
            if '{0.reaction.emoji}'.format(res) == '👍': await check_url(url, author.id, channel)

    else:
        await bot.send_message(channel, f":warning: **Je n'ai trouvé aucun résultat** pour *{recherche}*, désolé.")

#### Check user
@bot.event
async def check_user(message):
    plugdj_voice_channel = discord.utils.get(message.server.channels, id =plugdj_id)
    if message.author not in plugdj_voice_channel.voice_members:
        await bot.send_message(message.channel, f":no_entry_sign: <@{message.author.id}> Tu n'es pas connecté(e) sur le channel.")
        return False
    else:
        return True

@bot.event
async def remove_from_playlist(channel, author, number):
    try:
        if any(d["user"] == author.id for d in plugdj.liste):
            try:
                if plugdj.liste[int(number)-1]["user"] == author.id:
                    del plugdj.liste[int(number)-1]
                    await bot.send_message(channel, f":white_check_mark: <@{author.id}> La piste n°{number} a été supprimée de la playlist.")
                else:
                    await bot.send_message(channel, f":warning: <@{author.id}> La piste n°{number} a été proposée par une autre personne.")
            except:
                await bot.send_message(channel, f":warning: <@{author.id}> La piste n°{number} n'existe pas dans la playlist.")
        else:
            await bot.send_message(channel, f":warning: <@{author.id}> Tu n'as proposé aucune piste dans la playlist.")
    except:
        await bot.send_message(channel, f":warning: <@{author.id}> La playlist n'est pas initialisée.")

#### ON MESSAGE
@bot.event
async def on_message(message):

    ### Help command
    if message.content.lower().startswith('!help wolfram'):
        await bot.send_message(message.channel, help_text)

    ### Play command
    if message.content.lower().startswith('!play ') and await check_user(message):
        url = message.content.replace('!play ', '')
        await check_url(url, message.author.id, message.channel)

    ### Search command + searchance
    if message.content.lower().startswith('!search') and await check_user(message):
        recherche = message.content.replace("!searchance ", "").replace("!search ", "")
        chance = True if "chance" in message.content.lower() else False
        await search(message.channel, message.author, recherche, chance)

    ### Playing command
    if message.content.lower() in ['!playing', '!np']:
        await now_playing(message.channel)

    ### Playlist command
    if message.content.lower() in ['!playlist', '!pl']:
        await show_playlist(message.channel)

    ### "pp" shortcut command
    if message.content.lower().startswith('!pp'):
        await now_playing(message.channel)
        await show_playlist(message.channel)

    ### Skip command
    if message.content.lower().startswith('!skip') and await check_user(message):
        plugdj_voice_channel = discord.utils.get(message.server.channels, id =plugdj_id)
        await skip(message.channel, plugdj_voice_channel)

    ### Remove command
    if message.content.lower().startswith('!rm '):
        number = message.content.replace('!rm ', '')
        await remove_from_playlist(message.channel, message.author, number)

#### VOCAL
@bot.event
async def plugdj(url, titre, user, channel):

    try:
        plugdj.liste
    except AttributeError:
        plugdj.liste = []

    plugdj.liste.append({"url": url, "titre": titre, "user": user})

    try:
        if plugdj.player.is_playing():
            await bot.send_message(channel, f":white_check_mark: La piste *{titre}* proposée par <@{user}> a été ajoutée dans la playlist.")
            return
    except:
        try:
            if plugdj.running == True: return
        except:
            pass

    try:
        if plugdj.voice.is_connected() == False: plugdj.voice = await bot.join_voice_channel(plugdj_channel)
    except:
        plugdj.voice = await bot.join_voice_channel(plugdj_channel)

    while plugdj.liste != []:
        plugdj.running = True
        musique, plugdj.titre, plugdj.user, plugdj.liste = plugdj.liste[0]["url"], plugdj.liste[0]["titre"], plugdj.liste[0]["user"], plugdj.liste[1:]
        await bot.change_presence(game=discord.Game(name=plugdj.titre))
        plugdj.player = await plugdj.voice.create_ytdl_player(musique, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
        plugdj.player.start()
        plugdj.time = 0
        while plugdj.player.is_playing():
            await asyncio.sleep(1)
            plugdj.time += 1

    plugdj.running = False
    await plugdj.voice.disconnect()
    await bot.change_presence(game=discord.Game(name='doing nothing'))

#### Lancement du bot
bot.run(bot_secret)
