from datetime import datetime
import discord
from discord.ext import commands
import re
from utils.database import db
from utils.menu import Menu
from utils.page import Page


class MarriageCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def marriage(self, ctx):
        user = db['Users'].find_one({'_id': ctx.author.id})
        try:
            married_to = user['servers'][str(ctx.guild.id)]['married_to']
        except KeyError:
            await ctx.send("You are not married to anyone.")
        else:
            marriage_date = user['servers'][str(ctx.guild.id)]['marriage_date']
            days_married = int((datetime.utcnow() - marriage_date).total_seconds()/(3600*24))
            await ctx.send(f"You have been married to <@{married_to}> for {days_married} days! :heart:")

    @commands.command()
    @commands.guild_only()
    async def propose(self, ctx, member: discord.Member):
        try:
            is_proposer_married = db['Users'].find_one(
                {'_id': ctx.author.id})['servers'][str(ctx.guild.id)]['married_to']
        except KeyError:
            is_proposer_married = False

        try:
            is_proposed_married = db['Users'].find_one(
                {'_id': member.id})['servers'][str(ctx.guild.id)]['married_to']
        except KeyError:
            is_proposed_married = False

        if is_proposer_married or is_proposed_married:
            await ctx.send("Cannot propose to this person because either you or they are already married!")
            return

        def proposal_response_check(message):
            '''Check if:
                - Message by proposed member
                - Message in proposal channel
                - Message content is either "yes" or "no"
            '''
            return (
                message.author == member and
                message.channel == ctx.channel and
                re.search("(yes|no)", message.content, re.IGNORECASE)
            )

        proposal_page = Page (
            title=f"{ctx.author.mention} has proposed to {member.mention}! :heart:",
            content=f"{member.mention}, how do you respond? (yes/no)",
            footer="Type your answer in the chat below!"
        )

        menu = Menu (
            bot=self.bot,
            interactors=[member.id],
            pages=[proposal_page],
            channel=ctx.channel,
            input=proposal_response_check,
            show_buttons=False,
            remove_message_after=True
        )

        input_tuple = await menu.display()
        try:
            input, _ = input_tuple
            answer = input.content.lower()
        except TypeError:  # No response was given (tuple is empty)
            return

        await menu.stop()
        if answer == "no":
            await ctx.send("Ouch that must sting... :broken_heart:")
        else:
            date = datetime.utcnow()
            db['Users'].update_one({'_id': ctx.author.id},
                {'$set': {
                    f'servers.{ctx.guild.id}.married_to': member.id,
                    f'servers.{ctx.guild.id}.marriage_date': date
                    }
                }
            )
            db['Users'].update_one({'_id': member.id},
                {'$set': {
                    f'servers.{ctx.guild.id}.married_to': ctx.author.id,
                    f'servers.{ctx.guild.id}.marriage_date': date
                    }
                }
            )
            await ctx.send(f"Congratulations {member.name} & {ctx.author.name} are officially married! :heart:")

    @commands.command()
    @commands.guild_only()
    async def divorce(self, ctx):
        try:
            married_to = db['Users'].find_one(
                {'_id': ctx.author.id})['servers'][str(ctx.guild.id)]['married_to']
        except KeyError:
            married_to = None

        if not married_to:
            await ctx.send("You are not married... Therefore you cannot divorce anyone :s")
            return

        def confirmation_message_check(message):
            '''Check if:
                - Message by command invoker
                - Message in command invoked channel
                - Message content is either "yes" or "no"
            '''

            return (
                message.author == ctx.author and
                message.channel == ctx.channel and
                re.search("(yes|no)", message.content, re.IGNORECASE)
            )

        confirmation_page = Page (
            title=f"Are you sure you want to divorce <@{married_to}>?",
            content="Confirm your decision below. (yes/no)"
        )

        menu = Menu (
            bot=self.bot,
            interactors=[ctx.author.id],
            pages=[confirmation_page],
            channel=ctx.channel,
            input=confirmation_message_check,
            remove_message_after=True
        )

        input_tuple = await menu.display()
        try:
            input, _ = input_tuple
        except TypeError:
            return

        answer = input.content.lower()
        if answer == "no":
            return
        else:
            db['Users'].update_many({'_id': {'$in': [ctx.author.id, married_to]}},
                {'$unset': {
                    f'servers.{ctx.guild.id}.married_to': "",
                    f'servers.{ctx.guild.id}.marriage_date': ""
                    }
                }
            )
            await ctx.send(f"{ctx.author.mention} and <@{married_to}> are now officially divorced! :o")
        await menu.stop()


def setup(bot):
    bot.add_cog(MarriageCommandsCog(bot))
