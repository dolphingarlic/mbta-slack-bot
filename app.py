import os
from datetime import datetime

import aiohttp
from dateutil import parser
from slack_bolt.async_app import AsyncApp

API_URL = 'https://api-v3.mbta.com'
ASHMONT_QUERY = ('/predictions?sort=arrival_time'
                 '&fields%5Bprediction%5D=arrival_time'
                 '&filter%5Bstop%5D=70071')
ALEWIFE_QUERY = ('/predictions?sort=arrival_time'
                 '&fields%5Bprediction%5D=arrival_time'
                 '&filter%5Bstop%5D=70072')

app = AsyncApp(
    token=os.environ.get('SLACK_BOT_TOKEN'),
    signing_secret=os.environ.get('SLACK_SIGNING_SECRET')
)


def prediction_to_str(prediction):
    try:
        now = datetime.now()
        arrival = parser.parse(prediction['attributes']['arrival_time']).replace(tzinfo=None)
        minutes_diff = (arrival - now).seconds // 60
        if minutes_diff > 30:
            return ''
        if minutes_diff == 0:
            message = '*now*'
        else:
            message = f'in *{minutes_diff} minute{"s" if minutes_diff != 1 else ""}*'
        return f'Arriving {message} at {arrival.strftime("%H:%M")}'
    except:
        return ''


async def get_prediction_block():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL + ASHMONT_QUERY) as resp:
            ashmont_data = await resp.json()
            ashmont_messages = list(filter(lambda x: x != '', map(prediction_to_str, ashmont_data['data'])))
        async with session.get(API_URL + ALEWIFE_QUERY) as resp:
            alewife_data = await resp.json()
            alewife_messages = list(filter(lambda x: x != '', map(prediction_to_str, alewife_data['data'])))
    return [
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': 'Trains to Ashmont/Braintree',
                'emoji': True
            }
        },
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': '\n'.join(ashmont_messages)
            }
        },
        { 'type': 'divider' },
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': 'Trains to Alewife',
                'emoji': True
            }
        },
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': '\n'.join(alewife_messages)
            }
        },
    ]


@app.event('app_home_opened')
async def update_home_tab(client, event, logger):
    try:
        await client.views_publish(
            user_id=event['user'],
            view={
                'type': 'home',
                'callback_id': 'home_view',
                'blocks': [{
                    'type': 'header',
                    'text': {
                        'type': 'plain_text',
                        'text': 'Fetching arrival predictions :loading:',
                        'emoji': True
                    }
                }]
            }
        )
        await client.views_publish(
            user_id=event['user'],
            view={
                'type': 'home',
                'callback_id': 'home_view',
                'blocks': await get_prediction_block()
            }
        )
    except Exception as e:
        logger.error(f'Error publishing home tab: {e}')


@app.command('/mbta')
async def reply_with_schedule(ack, respond):
    await ack()
    try:
        await respond(blocks=await get_prediction_block())
    except:
        await respond('Oh no! Couldn\'t get the schedule :frowning:')


# Start your app
if __name__ == '__main__':
    app.start(port=int(os.environ.get('PORT', 3000)))
