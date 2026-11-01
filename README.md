### Office Bot

Apply for work from home, leave and petty cash from chat, in [Raven](https://github.com/frappe/raven) and Telegram. The commands do not depend on the chat app, so both work the same way and more channels can plug in later.

See the **[Office Bot User Manual](docs/user-manual.md)** for setup instructions, employee and approver workflows, examples, and troubleshooting.

### Commands

Type everything on one line, or leave parts out and the bot asks for them.

| Command | What it does | Example |
|---|---|---|
| `/wfh` | Work from home, submitted right away | `/wfh tomorrow`, `/wfh 3 nov to 5 nov`, `/wfh today half` |
| `/leave` | Leave application, sent to your leave approver | `/leave casual fri half`, `/leave sick 3 nov to 5 nov fever` |
| `/expense` | Petty cash expense | `/expense 250 food team lunch` |
| `/task` | Task in a remote Hive site | `/task Fix the login page` |
| `/balance` | Your leave balance | |
| `/my` | Your upcoming leave and work from home | |
| `/cancel` | Withdraw an upcoming work from home or a pending leave | |
| `/help` | List the commands | |

Dates can be `today`, `tomorrow`, `fri`, `next mon`, `5 nov` or `05-11-2026`. Type `stop` to end a question.

### Plain English

Turn on **Understand Plain English** in Office Bot Settings and people can skip the commands. They write "need wfh tomorrow" or "casual leave next friday, cousin's wedding", and the bot does the rest.

- An AI model only picks the command and fills in its words. It never writes a reply and never sees any records.
- Its answer goes through the same parsing and questions as a typed command. Anything missing is asked for.
- Before it creates or withdraws anything, the bot shows what it understood, for whom, and asks **Shall I go ahead?**
- Every request is for the person who wrote it. The model has no way to name another employee, and asks for someone else are refused.
- In Raven, write to the bot in a direct message or mention it in a channel. In Telegram, write in a direct message, or mention or reply to the bot in a group.

Choose a provider and tool-capable model in Office Bot Settings, then add its API key. The model list comes from the public catalog; custom OpenAI-compatible providers can use an API Base URL and model ID. See the [user manual](docs/user-manual.md#setup-plain-english-requests) for setup steps.

### How it works in Raven

- Talk to **Office Bot** in a direct message, or add the bot to a channel and type commands there.
- In a channel, a complete command runs at once. If something is missing, the bot asks in your direct message and posts the result back to the channel.
- Each result comes with a live card of the record.
- Each message's **Actions** menu has form versions of WFH, leave and petty cash.
- Leave approvers get a direct message with the leave card. They approve or reject it from the card's workflow menu. The employee gets a message when it is decided.
- At 10:30 the bot posts who is on leave and who is working from home to every channel it is in. It posts the WFH list again at 15:00.
- On the 1st of each month, last month's petty cash becomes one draft Journal Entry.

Commands run as the person who sent the message, with their own permissions. Two steps go further on purpose: submitting a WFH request, and withdrawing your own upcoming request. HRMS does not let the Employee role do those.

### How it works in Telegram

- Questions update in place as you answer, then become the result. Choices are buttons. Taps on an older question, or on someone else's question, are refused.
- In a direct message, just type your answers.
- In a group, questions stay in the group, because a bot cannot message someone who never opened a chat with it. Reply to the bot's current question to type an answer.
- In groups, the bot only reads commands, @mentions of the bot and replies to its own messages, not normal chatter.
- Results link to the record in the desk.
- Leave approvers and employees get the same messages as in Raven, if they have opened a chat with the bot. The daily lists go to every listed group.

### Setup

```bash
bench get-app https://github.com/gajjug004/office_bot --branch develop
bench --site <site> install-app office_bot
```

Office Bot needs Frappe HR and Raven on the same site. Installing it adds:

- the **Office Bot** Raven bot
- the three Message Actions
- four petty cash categories
- a **Leave Approval** workflow on Leave Application, unless the site already has a leave workflow
- a **Total WFH Days** field on Attendance Request

Then open **Office Bot Settings** and set:

- **Default Company** and **Default Cash Account** for the monthly petty cash entry, plus an expense account on each Petty Cash Category.
- **Hive Sites**, if you use `/task`.

Add the bot to the Raven channels where people should use it.

For Telegram:

1. Create a bot with [@BotFather](https://t.me/BotFather) and paste its token into **Bot Token** in Office Bot Settings.
   To let people @mention the bot in groups, send `/setprivacy` to @BotFather and pick **Disable**. With privacy mode on, Telegram only passes commands and replies to the bot. If the bot is already in a group, remove it and add it back after the change.
2. Click **Connect Telegram**. The site must be reachable over HTTPS. This points Telegram at the site and fills the bot's command menu.
3. Add each person under **Telegram Users** with their username. Their ID is saved the first time they write. People the bot does not know are told their ID when they send a command.
4. Add the bot to your groups and send any command. The bot replies with the group's chat ID. Add it under **Telegram Groups**.

### Tests

```bash
bench --site <site> run-tests --app office_bot
```

### License

mit
