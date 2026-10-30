### Office Bot

Apply for work from home, leave and petty cash from chat. Works in [Raven](https://github.com/frappe/raven) today. The commands do not depend on the chat app, so other channels such as Telegram can plug in later.

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

### How it works in Raven

- Talk to **Office Bot** in a direct message, or add the bot to a channel and type commands there.
- In a channel, a complete command runs at once. If something is missing, the bot asks in your direct message and posts the result back to the channel.
- Each result comes with a live card of the record.
- Each message's **Actions** menu has form versions of WFH, leave and petty cash.
- Leave approvers get a direct message with the leave card. They approve or reject it from the card's workflow menu. The employee gets a message when it is decided.
- At 10:30 the bot posts who is on leave and who is working from home to every channel it is in. It posts the WFH list again at 15:00.
- On the 1st of each month, last month's petty cash becomes one draft Journal Entry.

Commands run as the person who sent the message, with their own permissions. Two steps go further on purpose: submitting a WFH request, and withdrawing your own upcoming request. HRMS does not let the Employee role do those.

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

### Tests

```bash
bench --site <site> run-tests --app office_bot
```

### License

mit
