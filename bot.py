import telebot
import config
import flask
import json
import sys
import re
import requests

bot = telebot.TeleBot(config.TOKEN)

app = flask.Flask(__name__)

REST_URL = '/rest/webhooks/1.0/webhook'

chat_ids = []

SERVER = ''
USER = ''
API_KEY = ''


@app.route('/', methods=['POST'])
def telegram_hook():
	if flask.request.headers.get('content-type') == 'application/json':
		json_string = flask.request.get_data().decode('utf-8')
		update = telebot.types.Update.de_json(json_string)
		bot.process_new_updates([update])
		return flask.make_response('ok', 200)
	else:
		flask.abort(403)

@app.route('/jira', methods=['POST'])
def jira_hook():
		jdata = json.loads(flask.request.data)
		if jdata['webhookEvent'] == 'jira:issue_created':
			key = jdata['issue']['key']
			summary = jdata['issue']['fields']['summary']
			user = jdata['user']['displayName']
			msg = key + ' The issue ' + summary + ' was created by ' + user
			for chat_id in chat_ids:
				bot.send_message(chat_id, msg)
			return flask.make_response('ok', 200)
		elif jdata['webhookEvent'] == 'jira:issue_updated':
			key = jdata['issue']['key']
			summary = jdata['issue']['fields']['summary']
			user = jdata['user']['displayName']
			msg = key + ' The issue ' + summary + ' was updated by ' + user
			for chat_id in chat_ids:
				bot.send_message(chat_id, msg)
			return flask.make_response('ok', 200)

def jira_login(chat_id):
	bot.send_message(chat_id, 'Enter your Jira server address with command /server "server"')
	bot.send_message(chat_id, 'Enter your Jira login (email) with command /user "user"')
	bot.send_message(chat_id, 'Enter your Jira <a href="https://confluence.atlassian.com/cloud/api-tokens-938839638.html"> api key </a> with command /apikey "apikey"',
		parse_mode='html')


NAME = ''
JQL = ''
EVENTS = []

def get_hook_information(chat_id):
	bot.send_message(chat_id, 'Enter name of new webhook with command /name "Hook name"')
	bot.send_message(chat_id, 'Enter <a href="https://support.atlassian.com/jira-software-cloud/docs/what-is-advanced-searching-in-jira-cloud/">jql filter</a> with command /jql "YOUR FILTER"',
		parse_mode='html')
	bot.send_message(chat_id, 'Enter <a href="https://developer.atlassian.com/server/jira/platform/webhooks/#configuring-a-webhook">list of events</a> that you want to track with command /events "events separated with whitespace"',
		parse_mode='html')

@bot.message_handler(commands=['name'])
def get_hook_name(message):
	global NAME
	NAME = message.text[6:]

@bot.message_handler(commands=['jql'])
def get_hook_filter(message):
	global JQL
	JQL = message.text[5:]

@bot.message_handler(commands=['events'])
def get_hook_events(message):
	events = message.text.split(' ')[1:]
	for event in events:
		EVENTS.append(event)


@bot.message_handler(commands=['start'])
def welcome(message):
	chat_ids.append(message.chat.id)
	sticker = open('static/welcome.tgs', 'rb')
	bot.send_sticker(message.chat.id, sticker)
	markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
	item1 = telebot.types.KeyboardButton('🌚 Create new webhook')
	item2 = telebot.types.KeyboardButton('🌝 I have a webhook')
	markup.add(item1, item2)
	bot.send_message(message.chat.id,
		"Welcome, {0.first_name}!\nI'm - <b>{1.first_name}</b>, bot designed to work with Jira."
		.format(message.from_user, bot.get_me()),
        parse_mode='html', reply_markup=markup)

@bot.message_handler(commands=['server'])
def get_jira_server(message):
	global SERVER
	SERVER = message.text[8:]

@bot.message_handler(commands=['user'])
def get_jira_user(message):
	global USER
	USER = message.text[6:]

@bot.message_handler(commands=['apikey'])
def get_jira_apikey(message):
	global API_KEY
	API_KEY = message.text[8:]

@bot.message_handler(commands=['create'])
def post_hook(message):
	request = {'name' : NAME, 'url' : config.URL + '/jira', 'events' : EVENTS, 'filters' : {'issue-related-events-section' : JQL}}
	result = requests.post(SERVER + REST_URL, json=request, auth=(USER, API_KEY))
	print(result.text, sys.stderr)

@bot.message_handler(commands=['check'])
def check_hooks(message):
	result = requests.get(SERVER + REST_URL, auth=(USER, API_KEY))
	for hook in result.json():
		if hook['url'] != config.URL + '/jira':
			hook['url'] = config.URL + '/jira'
			result = requests.put(hook['self'], json=hook, auth=(USER, API_KEY))
			print(result.text, sys.stderr)
		

@bot.message_handler(func=lambda message : True, content_types=['text'])
def handle_all_messages(message):
	if message.text == '🌚 Create new webhook':
		if (not SERVER or not USER or not API_KEY):
			bot.send_message(message.chat.id, 'You need to log in jira before')
			jira_login(message.chat.id)
		get_hook_information(message.chat.id)
		bot.send_message(message.chat.id, 'After you enter all information create webhook with command /create')
	elif message.text == '🌝 I have a webhook':
		bot.send_message(message.chat.id, 'Be sure that your webhooks send messages on ' +
			config.URL + '/jira')
		bot.send_message(message.chat.id, 'Or if you want I can check it, just log in and run command /check')
		if (not SERVER or not USER or not API_KEY):
			jira_login(message.chat.id)
	else:
		bot.send_message(message.chat.id, "I don't know this command")



if __name__ == '__main__':
	app.run(host='127.0.0.1', debug=True)