from datetime import datetime
import dateparser
import pytz
from Event import Event
import asyncio
from dotenv import load_dotenv
import os


class EventManager(object):
    def __init__(self):
        self.dictionary = {}
        load_dotenv()
        self.discordTimezoneStr = os.getenv('discordTimezone')
        self.serverTimezoneStr = os.getenv('serverTimezone')
        self.discordTimezone = pytz.timezone(self.discordTimezoneStr)
        self.serverTimezone = pytz.timezone(self.serverTimezoneStr)
        self.settings = {'TIMEZONE': self.discordTimezoneStr, 'TO_TIMEZONE': self.serverTimezoneStr,
                         'RETURN_AS_TIMEZONE_AWARE': True, 'PREFER_DATES_FROM': 'future'}

    async def addEvent(self, ctx, message: str, time: str) -> None:
        """
        Adds a new event to the dictionary, with accurate time
        :param ctx: ctx the message should be sent to
        :type ctx:
        :param message: The message the event will send
        :type message: str
        :param time: the time the message should be sent
        :type time: str
        :return:
        :rtype: None
        """
        try: # try to parse the date from user input
            timeToSend = dateparser.parse(time, settings=self.settings)
        except ValueError: # if the date is not in a recognised format
            await ctx.reply('That date was not in a recognized format.')
            return
        if timeToSend is None: # if no date is provided
            await ctx.reply('That date was not in a recognized format.')
            return
        if datetime.now(self.serverTimezone) < timeToSend:  # If the event is in the future
            # create a new event, with user-given message, user-given time and pre-defined timezone
            eventAdded = Event(ctx, message, timeToSend, self.serverTimezone)

            # determine how many seconds still remain until the event happens
            eventAdded.future = asyncio.create_task(makeCallback(eventAdded.secondsRemaining(), self.sendEvent(eventAdded)))
            
            self.dictionary[hash(eventAdded)] = eventAdded # add new event as value to the events dictionary
            await ctx.reply(f"Event created. ID:{hash(eventAdded)}")
        else: # if the time given is in the past
            await ctx.reply('Please enter a time in the future.')

    async def sendEvent(self, event: Event):
        """
        Sends the specified event
        :param event: The event to send
        :return: None
        """
        await event.ctx.send(event.message)
        self.removeEvent(event)

    def removeEvent(self, event: Event) -> None:
        """
        Removes an event from the dictionary
        :param event: The event to be removed
        :return: None
        """
        event.future.cancel()
        try:
            del self.dictionary[hash(event)]
        except KeyError:  # if that event is not in the dictionary
            pass  # it was deleted before the message was sent

    def listEvents(self) -> str:
        """
        Creates a list of all upcoming events
        :return: A string with each event's details listed.
        """
        eventString = ''
        if len(self.dictionary) == 0:
            eventString = 'None'
        for event in self.dictionary.items():
            eventString += f"\nID: {hash(event[1])} \t " \
                           f"Date: {event[1].time.astimezone(self.discordTimezone).strftime('%m/%d/%Y %H:%M')} \n" \
                           "User: " + str("'" + event[1].ctx.message.author.display_name + "'                         ")[:19] + "\t" \
                           f"Message: \"{event[1].message}\"\n" #Find a better way to justify the Message section ^^^ Sucks
        return eventString

    def removeEventByKey(self, eventKey: int) -> None:
        """
        Removes an event based on it's hash
        :param eventKey: The integer hash of the event to be deleted
        :return: None
        """
        self.removeEvent(self.dictionary[eventKey]) # remove the given event from the events dictionary

    def numEvents(self) -> int:
        """
        The number of upcoming events
        :return: The number of events
        """
        return len(self.dictionary)

    def clearEvents(self) -> None:
        """
        Deletes all events
        :return: None
        """
        for event in self.dictionary.items():
            event[1].future.cancel()
        self.dictionary.clear()


async def makeCallback(seconds: int, callbackFunction):
    await asyncio.sleep(seconds)
    await callbackFunction
