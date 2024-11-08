# PL-UA QuizBot

PL-UA QuizBot is a Telegram bot designed to help users practice Polish and Ukrainian vocabulary through quiz-based polls. The bot automatically sends scheduled quiz questions to multiple Telegram channels, allowing users to learn new words in a fun, interactive way.

## Features

- **Schedule Polls**: Conduct polls at specific times according to a predefined schedule.
- **Add Channels**: Users can add their Telegram channels to the bot to host the polls.
- **Word List**: The bot uses a list of words (with options and correct answers) for the quiz.
- **Time Zone Support**: The bot uses the Warsaw time zone (Europe/Warsaw) for scheduling.

## Setup

1. **Clone the Repository**:
```bash
git clone https://github.com/Vagalep/pl-ua-quiz-bot.git
cd QuizBot
```
2. **Install the required Python packages**:
```bash
pip install -r requirements.txt
```
   
3. **Configuration**:
- Create a config.json file with your bot token and Telegram channels:
```json
{
  "token": "your_telegram_bot_token",
  "channel_names": ["@channel1", "@channel2"]
}
```
- Set up the schedule in schedule.json. Specify the hours and minutes for each poll (in Warsaw local time):
```json
[
  {"hour": 9, "minute": 0},
  {"hour": 14, "minute": 0},
  {"hour": 17, "minute": 0},
  {"hour": 21, "minute": 0}
]
```
4. **Run the Bot: Start the bot with**:
```bash
python quiz_bot.py
```

## Files

- **quiz_bot.py**: The main script for running the bot.
- **config.json**: Stores the bot token and list of channels.
- **schedule.json**: Defines the schedule for poll times.
- **words.json**: Contains vocabulary questions and answers.

## Requirements

- Make sure you have the following dependencies installed, which are listed in requirements.txt:
```plaintext
python-telegram-bot==20.0  # or the correct version you're using
pytz
httpx
```
- Install them by running:
```bash
pip install -r requirements.txt
```
## How It Works

1. The bot checks the schedule.json file to configure when to send polls.
2. At each scheduled time, the bot randomly picks a word from the words.json file and sends a quiz to the specified channels.
3. If a user adds a channel with /add @channel_name, the bot verifies if it is a member of that channel and adds it to the list of channels for future polls.

## License

This project is licensed under the MIT License.