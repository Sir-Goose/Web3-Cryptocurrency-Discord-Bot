import os
import discord
import pandas as pd
from discord.ext import commands, tasks
from discord import app_commands
import time
from datetime import datetime
import pickle

import charting
import formatter
import price

intents = discord.Intents.default()
intents.presences = True
intents.message_content = True

client = discord.Client(intents=intents)

tree = app_commands.CommandTree(client)

cg_tokens_dict = pd.read_csv('cgtokens.csv', header=None, index_col=0).iloc[:, 0].to_dict()
print("csv loaded")

reminder_dictionary = {}



@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    # lists servers bot is in
    print(client.guilds)
    await tree.sync()
    print("Commands Synced")
    set_status.start()
    remind.start()

def get_status():
    status = price.get_imp_price("imp")
    status = formatter.format_imp_status(status)
    return status


@tasks.loop(minutes=30)
async def set_status():
    print("Attempting to set status")
    status = get_status()
    await client.change_presence(activity=discord.Game(name=status))
    print(f'Status updated to: {status}')


@tasks.loop(seconds=60)
async def remind():
    print("Checking reminders")
    current_time = int(time.time())
    executed_reminder_key = None
    for key in reminder_dictionary:
        if key <= current_time:
            await reminder_dictionary[key][1].send("Reminder for " + str(reminder_dictionary[key][2]) + ": " + reminder_dictionary[key][0], reference=reminder_dictionary[key][3])
            executed_reminder_key = key
    if executed_reminder_key is not None:
        del reminder_dictionary[executed_reminder_key]


def set_reminder(message):
    message_content_list = message.content.split()
    print(message_content_list[0])
    if "$remindme" == message_content_list[0]:
        #remind_time = int(message_content_list[1])
        #remind_time += int(time.time())
        time_string = message_content_list[1] + " " + message_content_list[2]
        time_format = "%Y-%m-%d %H:%M"

        # Convert the time string to a datetime object
        datetime_object = datetime.strptime(time_string, time_format)

        # Convert the datetime object to UTC time in seconds
        utc_time_in_seconds = int(datetime_object.timestamp())
        remind_time = utc_time_in_seconds

        remind_message = " ".join(message_content_list[3:])
        reminder_details = [remind_message, message.channel, message.author, message]
        reminder_dictionary[remind_time] = reminder_details


        return remind_time


async def send_reminder(message, remind_time):
    utc_time = datetime.utcfromtimestamp(remind_time)
    human_readable_utc_time = utc_time.strftime("%Y-%m-%d %H:%M:%S")

    print("Human-readable UTC time:", human_readable_utc_time)
    await message.channel.send("Reminder set for " + str(human_readable_utc_time))


@tree.command(name="imp", description="Fetch the price of IMP", guild=discord.Object(id=913038008624750653))
async def slash_imp(interaction):
    await interaction.response.send_message("Deez nutz")


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    print(f"{message.author}: {message.content}")
    is_meta = meta_joke(message.content)
    if is_meta:
        reply = "Did you mean Facebook?"
        await message.channel.send(reply, reference=message)
        print(f"<{reply}>")
        return

    message_content_list = message.content.split()
    if "$remindme" == message_content_list[0]:
        remind_time = set_reminder(message)
        human_readable_utc_time = datetime.utcfromtimestamp(remind_time).strftime("%Y-%m-%d %H:%M")
        await message.channel.send("Reminder set for " + str(human_readable_utc_time), reference=message)

    user_message_list = message.content.split()
    print(user_message_list)
    output = control_flow(user_message_list)
    if output is None:
        return
    elif output == 'chart.png':
        print("sending chart")
        with open('chart.png', 'rb') as chart:

            picture = discord.File(chart)
            await message.channel.send(file=picture, reference=message)
    elif output != True:
        print(f"<{output}>")
        await message.channel.send(output, reference=message)
    elif output:
        emoji = '\N{THUMBS UP SIGN}'
        await message.add_reaction(emoji)
        print(f"<{emoji}>")
        return


def control_flow(user_message_list):
    user_message_prefix = user_message_list[0].lower()
    try:
        token = user_message_list[1].lower()
        period = user_message_list[2].lower()
        interval = user_message_list[3].lower()
        date = user_message_list[2]
    except IndexError:
        pass

    if user_message_prefix == '$p':

        if token == 'imp':
            'imp_price'
            output = price.get_imp_price(token)
            output = formatter.format_imp(output)
            return output
        if token == 'multi-dai-ftm':
            output = price.get_multi_dai_price(token)
            output = formatter.format_multi_dai(output)

        else:
            type = 'current'
            output_list = price.get_cg_price(token, type, cg_tokens_dict)
            output = formatter.format_cg(output_list)
            return output

    if user_message_prefix == '$h':
        if token == 'imp':
            ...
        else:
            output, token_id = price.get_historical_price_cg(token, date, cg_tokens_dict)
            output = formatter.format_historical_cg(output, date, token_id)
            return output

    if user_message_prefix == '$request':
        bool = record_request(user_message_list)
        if bool:
            return True

    if user_message_prefix == '$convert':
        output = convert_tokens(user_message_list, cg_tokens_dict)
        output = formatter.format_conversion(output)
        return output

    if user_message_prefix == '$imp':
        token = 'imp'
        type = 'imp_price'
        output = price.get_imp_price(token)
        output = formatter.format_imp(output)
        return output

    if user_message_prefix == '$s' or user_message_prefix == '$stock':
        output = price.get_stock_price(token)
        output = formatter.format_stock(token, output)
        return output

    if user_message_prefix == '$c' or user_message_prefix == '$chart':
        output = charting.get_chart(token, period, interval)
        return output


def convert_tokens(user_message_list, cg_tokens_dict):
    quantity_one = user_message_list[1]
    token_one = user_message_list[2]
    token_two = user_message_list[3]

    type = 'current'
    token_one_price = price.get_cg_price(token_one, type, cg_tokens_dict)
    token_one_price = token_one_price[0].replace(',', '')

    token_two_price = price.get_cg_price(token_two, type, cg_tokens_dict)
    token_two_price = token_two_price[0].replace(',', '')

    output = (float(token_one_price) * float(quantity_one)) / float(token_two_price)
    return output


def record_request(user_message_list):
    message_text = ' '.join(user_message_list)

    with open('requests.txt', 'a') as external_file:
        print(message_text, file=external_file)
        external_file.close()
        return True


def meta_joke(message):
    message = message.split()
    for i in range(len(message)):
        if message[i].lower() == 'meta':
            return True
        else:
            return False


# Put your token here
client.run('')
