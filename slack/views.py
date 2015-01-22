from bot import SlackBot
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from slack.models import SlackUser
import cleverbot
import json
import re


@require_POST
def command_webhook(request):
    """
    Handle data from a webhook
    """
    info_url = "https://www.changetip.com/tip-online/slack"
    get_started = "To send your first tip, login with your slack account on ChangeTip: %s" % info_url
    print(json.dumps(request.POST.copy(), indent=2))

    # Do we have this user?
    user_name = request.POST.get("user_name")
    slack_sender, created = SlackUser.objects.get_or_create(
        name=user_name,
        team_id=request.POST.get("team_id"),
        user_id=request.POST.get("user_id"),
    )
    if created:
        return JsonResponse({"text": "Nice to meet you, %s! %s" % (user_name, get_started)})

    text = request.POST.get("text", "")

    # Check for mentions in the format of <@$userid>
    bot = SlackBot()
    mention_matches = bot.get_mentions(text)
    if not mention_matches:
        # Say something clever
        cb = cleverbot.Cleverbot()
        response = cb.ask(text.replace('changetip', ''))
        return JsonResponse({"text": response})

    slack_receivers = SlackUser.objects.filter(
        team_id = slack_sender.team_id,
        user_id__in=[m.group(1) for m in mention_matches]
    )

    if not slack_receivers:
        return JsonResponse({"text": "%s, I don't know who that person is yet. They should say hi to me before I give them money." % user_name})

    # Check for requests to make it rain
    if re.search(r"make it ra+i+n", text, re.IGNORECASE):
        recipient_limit = 50 # Sane?
    else:
        recipient_limit = 1

    # Submit the tips
    team_domain = request.POST.get("team_domain")

        out = ""
    for i, receiver in enumerate(slack_receivers):
        if i >= recipient_limit:
            break
        tip_data = {
            "sender": "%s@%s" % (slack_sender.namze, team_domain),
            "receiver": "%s@%s" % (receiver.name, team_domain),
            "message": text,
            "context_uid": bot.unique_id(request.POST.copy()),
            "meta": {}
        }
        for meta_field in ["token", "team_id", "channel_id", "channel_name", "user_id", "user_name", "command"]:
            tip_data["meta"][meta_field] = request.POST.get(meta_field)

        if request.POST.get("noop"):
            return JsonResponse({"text": "Hi!"})

        response = bot.send_tip(**tip_data)
        if out:
            out += "\n"
        if response.get("error_code") == "invalid_sender":
            out = get_started
        elif response.get("error_code") == "duplicate_context_uid":
            out = "That looks like a duplicate tip."
        elif response.get("error_message"):
            out = response.get("error_message")
        elif response.get("state") in ["ok", "accepted"]:
            tip = response["tip"]
            if tip["status"] == "out for delivery":
                out += "The tip for %s is out for delivery. %s needs to collect by connecting their ChangeTip account to slack at %s" % (tip["amount_display"], tip["receiver"], info_url)
            elif tip["status"] == "finished":
                out += "The tip has been delivered, %s has been added to %s's ChangeTip wallet." % (tip["amount_display"], tip["receiver"])

        if "+debug" in text:
            out += "\n```\n%s\n```" % json.dumps(response, indent=2)

    return JsonResponse({"text": out})


def home(request):
    return HttpResponse("OK")
