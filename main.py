import httpx
import asyncio
import ollama
import subprocess
import discord
from discord.ext import commands
from discord import Intents
import requests 
import base64
import mysql.connector


db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="0uyraqqnww",
    database="chatlogs",
)

mycursor = db.cursor(buffered=True)
#mycursor.execute("SHOW DATABASES")

token = "MTE4ODM4ODExMjk4OTE3NTg2OQ.GrZaTd.mLr_4MFMRoCWJ3FJmZxzFwdzpzeD96zbEqAbDI"
intents = Intents.default()
intents.message_content = True
#client = discord.Client(intents = intents)
bot = commands.Bot(command_prefix='!', intents = intents)
my_dictionary =   {
    "model":"mistral",
    "lang":"english",
    "ctx":[],
    "counter":1
}
my_ollama = ollama.AsyncClient()

#commands
#change model, change landuage, start new convo,
@bot.command()
async def pull(ctx, model):
    print("ran")
    reply = await ctx.channel.send(f'Pulling {model} from Ollama...')
    try:
        pull = await my_ollama.pull(model)
        print(pull)
        if pull['status'] == "success":
            my_dictionary["model"] = model
            await bot.change_presence(activity = discord.Game(my_dictionary["model"]))
            await reply.edit(content = f'Now using {model}')
    except:
        await reply.edit(content = f"Sorry, we don't have {model} yet")
        await model(ctx)

@bot.command()
async def lang(ctx, lang):
    print("change lang")
    reply = await ctx.channel.send(f'Learning to speak {lang}')
    my_dictionary["lang"] = lang

@bot.command()
async def default(ctx):
    print("resetting to defaults")
    reply = await ctx.channel.send(f'Back to default settings.')
    my_dictionary["model"] = "mistral"
    my_dictionary["lang"] = "english"
    my_dictionary["ctx"] = []

@bot.command()
async def newconvo(ctx):
    my_dictionary['counter'] = my_dictionary['counter'] + 1
    print("reset conversation")
    my_dictionary["ctx"] = []
    mycursor.execute(f"CREATE TABLE convo{str(my_dictionary['counter'])} (message VARCHAR(255), ctx TEXT)")
    mycursor.execute(f"DELETE FROM counter")
    mycursor.execute(f"INSERT INTO counter VALUES ({my_dictionary['counter']})")
    print(my_dictionary["counter"])

@bot.command()
async def model(ctx):
    reply = await ctx.channel.send(f'Find available models to run here: https://ollama.ai/library')

@bot.command()
async def deleteconvo(ctx, convo):
    mycursor.execute(f"DROP TABLE IF EXISTS {convo}")

@bot.command
async def convos(ctx):
    mycursor.execute("SHOW TABLES")
    

#DEBUG
@bot.command()
async def ctx(ctx):
    mycursor.execute(f"SHOW DATABASES")
    for x in mycursor:
        print(x)
    print("new section--------------c")
    mycursor.execute("SHOW TABLES")
    for x in mycursor:
        print(x)

@bot.command()
async def table(ctx, num):
    mycursor.execute(f"SELECT ctx FROM {num}")
    myresult = mycursor.fetchall()
    for x in myresult:
        print(x)

@bot.command()
async def convo(ctx, num):
    await ctx.channel.send("Changing conversations")
    mycursor.execute(f"SELECT ctx FROM convo{num}")
    myresult = mycursor.fetchall()
    counter = 1
    for x in myresult:
        if counter == len(myresult):
            result = x[0].split(",")
            result[0] = result[0].replace("[", "")
            result[len(result) - 1] = result[len(result) - 1].replace("]", "")
            my_dictionary["ctx"] = list(map(int, result))
        else: 
            counter = counter + 1

    my_dictionary["counter"] = int(num)

@bot.event
async def on_ready():
    cmd = "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'counter'"
    mycursor.execute(cmd)
    if mycursor.fetchone()[0] == 1:
        print("here")
        mycursor.execute("SELECT counter FROM counter")
        my_dictionary['counter'] = int(mycursor.fetchone()[0])
    else:
        print("not")
        mycursor.execute(f"CREATE TABLE counter (counter TEXT)")
        sql = f"INSERT INTO counter VALUES ({my_dictionary['counter']})"
        mycursor.execute(sql)
        db.commit()

    print("captain teemo, on duty!")
    await bot.change_presence(activity = discord.Game(my_dictionary["model"]))

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    print(message.attachments)
    context = my_dictionary["ctx"]
    print(context)
    output = ""
    #while True:
       #prompt = input("What do you wanna ask mistral? ")
    if message.author == bot.user:
        return
   
    if bot.user.mentioned_in(message):
        sql = f"INSERT INTO convo{str(my_dictionary['counter'])} (message, ctx) VALUES (%s, %s)"
        #print(message.content)
        message.content = message.content.replace("<@1188388112989175869>", "")
        #print(message.content)
        images = []
        for i in message.attachments:
            images.append(encode(i.url))
        if (images == [] or my_dictionary["model"] != "llava") and message.content == "" :
            return

        task = asyncio.create_task(thinking(message))
        buffered = ''
        # reply = await message.channel.send(output)
        output = ""
        first_message = True
        # async with message.channel.typing():
        await bot.change_presence(activity=discord.CustomActivity("🤔"))
        if(images != [] and my_dictionary["model"] == "llava"):
            await llava(message, context, images, task, output, buffered)
            return
        
        async for i in await my_ollama.generate(my_dictionary["model"], system=f'respond in {my_dictionary["lang"]} and keep answer under 2000 characters', 
                                  prompt=message.content, stream=True, context=context):
            #print(i)
            if i["done"] == True:
                print(i['context'])
                my_dictionary["ctx"] = i["context"]
                val = (message.content, str(i["context"]))
                mycursor.execute(sql, val)
                db.commit()
                print(val)
                print(my_dictionary['counter'])

            else:
                print(i["response"], end="", flush=True)
                output += i["response"]
                buffered += i['response']
            #if buffered[len(buffered)-1:len(buffered)] in ['.', '?', '!', ',' ':', '！', '。', '，', '\n'] and len(buffered) > 1:
            if len(buffered) > 37:
                if first_message:
                    reply = await message.channel.send(output)
                    task.cancel()
                    first_message = False
                else:
                    await reply.edit(content=output)
                #subprocess.call(['say', '-v', 'Tingting', buffered])
                buffered = ''
        if buffered:
            await reply.edit(content=output)
            #subprocess.call(['say', '-v', 'Tingting', buffered])
        print()
        await bot.change_presence(activity=discord.Game(my_dictionary["model"]))
        
async def llava(message, context, images, task, output, buffered):
    first_message = True

    if message.content == "":
        message.content = "Analyze this image"
    
    async for i in await my_ollama.generate(my_dictionary["model"], prompt=message.content, stream=True, context=context, images=images):
            #print(i)
        if i["done"] == True:
            my_dictionary["ctx"] = i["context"]
        else:
            print(i["response"], end="", flush=True)
            output += i["response"]
            buffered += i['response']
        #if buffered[len(buffered)-1:len(buffered)] in ['.', '?', '!', ',' ':', '！', '。', '，', '\n'] and len(buffered) > 1:
        if len(buffered) > 37:
            if first_message:
                reply = await message.channel.send(output)
                task.cancel()
                first_message = False
            else:
                await reply.edit(content=output)
            #subprocess.call(['say', '-v', 'Tingting', buffered])
            buffered = ''
    if buffered:
        await reply.edit(content=output)
        #subprocess.call(['say', '-v', 'Tingting', buffered])
    print()
    await bot.change_presence(activity=discord.Game(my_dictionary["model"]))


async def thinking(message):
    timeout = 999
    try:
        await message.add_reaction('🤔')
        async with message.channel.typing():
            print("typing")
            await asyncio.sleep(timeout)
    except Exception as e:
        print("failed")
    finally:
        await message.remove_reaction('🤔', bot.user)

def encode(url):
    return base64.b64encode(requests.get(url).content)
    
#client.run(token)
bot.run(token)
