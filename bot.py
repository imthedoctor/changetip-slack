from changetip.bots.base import BaseBot
import datetime
import hashlib
import os

CHANGETIP_API_KEY = os.getenv("CHANGETIP_API_KEY")
assert CHANGETIP_API_KEY, "CHANGETIP_API_KEY environment variable must be set. To get one, contact support@changetip.com"


class SlackBot(BaseBot):

    channel = "slack"
    changetip_api_key = CHANGETIP_API_KEY
    wrappers = ('(',')')

    def unique_id(self, post_data):
        # Generatee a special id to prevent duplicates.
        checksum = hashlib.md5()
        checksum.update(str(post_data).encode("utf8"))

        # Now we also include a time stamp for entry.
        # Note it is to the minute, so that people can send the same tip a little later
        # The idea here is that we want to prevent dupelicates, but not prevent the same tip a minute later
        checksum.update(datetime.datetime.now().strftime('%Y-%m-%d:%H:%M:00').encode("utf8"))

        return checksum.hexdigest()[:16]


    def get_mentions(self, message):
        """ Remove duplicates in a case-insensitive way while preserving the original order
        Return all mentions in lower case *without* their prefixes. (So return ['clyde'], not ['@clyde'])
        >>> BaseBot().get_mentions("This is a @user")
        ['user']
        >>> BaseBot().get_mentions("This is empty")
        []
        >>> BaseBot().get_mentions("title case and end of string @mention @ChangeTip. and @")
        ['mention', 'changetip']
        >>> BaseBot().get_mentions("@ This one has an empty one and two @mention-69 @changetip.")
        ['mention-69', 'changetip']
        >>> BaseBot().get_mentions("This one has a dupe @mention-69 @changetip and @mention-69.")
        ['mention-69', 'changetip']
        >>> SlackBot().get_mentions("This one looks like <@postdata> <@usernames>")
        ['postdata', 'usernames']
        """
        mentions = re.findall(self.wrappers[0] + re.escape(self.prefix) + '([\w-]+)' + self.wrappers[1],
                              message)
        mentions_set = set([m.lower() for m in mentions])

        deduped_mentions = []
        for m in mentions:
            m = m.lower()
            if m in mentions_set:
                mentions_set.remove(m)
                deduped_mentions.append(m)

        return deduped_mentions
