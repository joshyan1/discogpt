import httpx
import asyncio
import ollama
import subprocess
import discord
from discord.ext import commands
from discord import Intents

token = "token"
intents = Intents.default()
intents.message_content = True
#client = discord.Client(intents = intents)
bot = commands.Bot(command_prefix='!', intents = intents)
my_dictionary =   {
    "model":"mistral",
    "lang":"english",
}

#commands
#change model, change landuage, start new convo,
@bot.command()
async def model(ctx, model):
    print("ran")
    reply = await ctx.channel.send(f'Pulling {model} from Ollama...')
    if ollama.pull(model)['status'] == "success":
        my_dictionary["model"] = model
        await bot.change_presence(activity=discord.Game(my_dictionary["model"]))
        await reply.edit(content = f'Now using {model}')
    else:
        await reply.edit(content = f"Sorry, we don't have {model} yet")

@bot.command()
async def lang(ctx, lang):
    print("change lang")
    reply = await ctx.channel.send(f'Learning to speak {lang}')
    my_dictionary["lang"] = lang


@bot.event
async def on_ready():
    print("captain teemo, on duty!")
    await bot.change_presence(activity = discord.Game(my_dictionary["model"]))

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    context = []
    output = "Generating response..."
    #while True:
       #prompt = input("What do you wanna ask mistral? ")
    if message.author == bot.user:
        return
   
    if bot.user.mentioned_in(message):
        buffered = ''
        reply = await message.channel.send(output)
        output = ""
        await bot.change_presence(activity=discord.CustomActivity("Thinking..."))
        for i  in ollama.generate(my_dictionary["model"], system=f'respond in {my_dictionary["lang"]}', 
                                  prompt=message.content, stream=True, context=context):
            if i["done"] == True:
                context = i["context"]
            else:
                print(i["response"], end="", flush=True)
                output += i["response"]
                buffered += i['response']
            if buffered[len(buffered)-1:len(buffered)] in ['.', '?', '!', ',' ':', '！', '。', '，', '\n'] and len(buffered) > 1:
                await reply.edit(content=output)
                #subprocess.call(['say', '-v', 'Tingting', buffered])
                buffered = ''
        if buffered:
            await reply.edit(content=output)
            #subprocess.call(['say', '-v', 'Tingting', buffered])
        print()
        await bot.change_presence(activity=discord.Game(my_dictionary["model"]))
        
    

#client.run(token)
bot.run(token)
