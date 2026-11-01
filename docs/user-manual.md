# Office Bot User Manual

Office Bot lets employees request work from home, apply for leave, record petty cash, and create Hive tasks from Raven or Telegram. The bot asks for any required details that are missing.

This manual covers installation and setup, daily use, approvals, and common problems.

## Contents

- [For employees](#for-employees)
- [Commands at a glance](#commands-at-a-glance)
- [Write a request](#write-a-request)
- [Use plain English](#use-plain-english)
- [Use Office Bot in Raven](#use-office-bot-in-raven)
- [Use Office Bot in Telegram](#use-office-bot-in-telegram)
- [For approvers](#for-approvers)
- [For administrators](#for-administrators)
- [Set up Raven](#set-up-raven)
- [Set up Telegram](#set-up-telegram)
- [Set up plain English requests](#set-up-plain-english-requests)
- [Set up petty cash and Hive](#set-up-petty-cash-and-hive)
- [Troubleshooting](#troubleshooting)

## For employees

1. Open a direct chat with **Office Bot** in Raven or Telegram. You can also use it in an enabled Raven channel or configured Telegram group.
2. Type `/help` to see the commands, or send a command such as `/wfh tomorrow`.
3. Answer the bot’s questions. In Telegram, use the buttons when they are shown. In a group, reply to the bot’s current question when you need to type an answer.
4. Check the summary and result. The bot links to the created record when the channel supports record links.

You can leave required details out of a command. The bot will ask for them. Type `stop`, `cancel`, `quit`, or `exit` during a question to stop; the bot will not create the request.

The bot links your chat account to your Frappe user, then uses the Employee linked to that user. If the user is not linked to an active Employee, ask HR to update your Employee record.

## Commands at a glance

| Command | Purpose | Example |
| --- | --- | --- |
| `/wfh` | Submit a work-from-home request | `/wfh tomorrow` |
| `/leave` | Apply for leave for your approver to review | `/leave casual fri half` |
| `/expense` | Record a petty cash expense | `/expense 250 Food team lunch` |
| `/task` | Create a task in a configured Hive site | `/task Fix the login page` |
| `/balance` | Show your allocated leave balances | `/balance` |
| `/my` | Show your upcoming leave and WFH | `/my` |
| `/cancel` | Withdraw an eligible upcoming request | `/cancel` |
| `/help` | Show the command list | `/help` |

Commands are available in Raven and Telegram. A command can include all details, or just the command name. For example, `/leave` starts a leave request and asks for the leave type and dates.

## Write a request

### Work from home

Use `/wfh` followed by a date or date range. Add `half` for a half day.

```text
/wfh tomorrow
/wfh 3 nov to 5 nov
/wfh today half
```

The bot submits the Attendance Request right away. A WFH request is auto-approved. It checks that there is no overlapping leave, attendance request, or already marked attendance. Holidays are not counted as WFH days.

### Leave

Use `/leave`, then a leave type, dates, and an optional reason.

```text
/leave casual tomorrow
/leave sick 3 nov to 5 nov fever
/leave casual fri half
```

The leave type must be available in your leave allocations. The request goes to your assigned leave approver. If you have no leave balance or no required approver is set, contact HR.

### Petty cash expense

Enter the amount first, then a configured category, an optional date, and a short description.

```text
/expense 250 Food team lunch
/expense 1200 Travel yesterday cab to client
```

The amount must be greater than zero. The category must match a Petty Cash Category configured by your administrator. If the date is omitted, the bot uses today. If a required detail is missing, the bot asks for it.

### Hive task

Start with `/task` and add a title. The bot asks for the remaining task details.

```text
/task Fix the login page
```

Depending on the configuration, it may ask for a Hive site, description, start date, due date, project, and assignees. It creates the task with status **To Do**. Hive must be configured by an administrator.

### Check or withdraw requests

```text
/balance
/my
/cancel
```

`/balance` lists leave allocations. `/my` lists upcoming leave and WFH. `/cancel` shows requests you can withdraw. You can withdraw your own pending leave or a WFH request that starts today or later. Approved leave must be cancelled by HR.

### Dates

You can use common date words or numeric dates:

```text
today
tomorrow
fri
next mon
5 nov
05/11/2026
2026-11-05
```

For example, `/leave sick 3 nov to 5 nov fever` uses the first date as the start and the last date as the end. Numeric dates with slashes are read day first, so `05/11/2026` means 5 November 2026. The bot uses the site’s current date when interpreting relative dates.

## Use plain English

If an administrator enables **Understand Plain English**, you can write a request without a slash command.

```text
I need to work from home tomorrow
Please apply for sick leave from 3 Nov to 5 Nov; I have a fever
I spent 250 on food for the team lunch
```

The bot interprets the message, then uses the same command checks and questions. Before it creates or withdraws a request, it shows a summary and asks for confirmation. Read the summary and confirm only if it is correct. Read-only commands such as `/balance` and `/my` do not need confirmation.

Plain English requests are always for the person who sent the message. The bot cannot submit a request on behalf of another employee. If the meaning is unclear, use a slash command or type `/help`.

## Use Office Bot in Raven

- In a direct message with **Office Bot**, send a command or plain English request.
- In a channel where Office Bot is a member, send a slash command or mention the bot.
- A complete command runs in the channel. If the bot needs more information, it sends the question by direct message. The final result is posted in the original channel.
- Use the **Actions** menu on a Raven message for **Apply for Work From Home**, **Apply for Leave**, or **Record Petty Cash Expense**.
- Created records link to their Frappe desk form.

Leave approvers receive a Raven direct message with the request and approval actions. Once the approver decides, the employee receives a message.

## Use Office Bot in Telegram

- In a direct chat with the bot, type a command or plain English request. Follow-up questions update in place; tap a button or type your answer.
- In a group, Office Bot responds to commands, messages that mention the bot, and replies to the bot’s current question. It ignores ordinary group chat.
- Reply to the bot’s current question when you need to type an answer in a group. The bot keeps the conversation in that group.
- The bot reacts with a thumbs-up when it receives a slash command.
- Older buttons or another person’s buttons cannot answer your current question.
- Leave approvers and employees can receive direct messages only after they have opened a chat with the bot.

The bot can use only configured Telegram groups. Ask an administrator to add a group if commands are ignored.

## For approvers

When an employee applies for leave, the assigned leave approver receives a direct message in each enabled channel where that approver is configured. The message includes the employee, leave type, dates, duration, and reason when provided.

- In Raven, open the leave card and use its workflow actions.
- In Telegram, use the **Approve** or **Reject** buttons in the notification.
- You can also open the Leave Application in Frappe and use the normal workflow.

Only the assigned approver or an HR Manager can decide the request through the bot. The site’s Leave Application workflow and permissions apply. The employee is notified after approval or rejection.

## For administrators

Office Bot requires Frappe HR (HRMS) and Raven installed on the same site. Install the app on the bench, then on the site:

```bash
bench get-app https://github.com/gajjug004/office_bot --branch develop
bench --site <site> install-app office_bot
```

After installation, open **Office Bot Settings** as a System Manager. The form has **General**, **Raven**, and **Telegram** tabs. Save changes after editing settings.

Installation creates the Office Bot Raven bot, three Raven Message Actions, default petty cash categories (Internet, Food, Stationery, Travel) when no categories exist, a Leave Approval workflow when there is no active leave workflow, and a Total WFH Days field on Attendance Request.

The app does not replace an active Leave Application workflow. Review the existing workflow and role permissions if approvers cannot act on bot notifications.

## Set up Raven

1. Open **Office Bot Settings** and go to **Raven**.
2. Make sure **Enable Raven** is on.
3. Select the **Office Bot** Raven Bot, if it is not already selected.
4. Add the bot to the Raven channels where employees should use it and where daily updates should appear.

Turn off **Enable Raven** to pause Raven commands and notifications. The 10:30 update lists employees on leave and working from home. The 15:00 update lists employees working from home. Updates are sent to non-direct-message Raven channels the bot belongs to, when there are people to report.

## Set up Telegram

1. Create a Telegram bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. In **Office Bot Settings → Telegram**, enable Telegram and paste the token into **Bot Token**. Save the settings.
3. Select **Connect Telegram**. The Frappe site must be reachable over HTTPS. This registers the webhook and fills Telegram’s slash-command menu. The connected bot can receive updates at one webhook URL; connecting it to another site moves it there.
4. Add each employee under **Telegram Users**. Select their Frappe **User** and enter their **Telegram Username**. The user ID is saved when they first write to the bot. If the bot does not recognize a sender, it replies with the Telegram ID; add that ID to the matching row.
5. Add the bot to each group. Send a command in the group. The bot replies with the group’s chat ID. Add that ID and an optional label under **Telegram Groups**, then save.
6. To let the bot respond to @mentions in a group, message @BotFather with `/setprivacy`, choose **Disable**, then remove the bot from the group and add it again. With privacy enabled, Telegram still passes commands and replies to the bot.

Turn off **Enable Telegram** to pause Telegram commands and alerts. Daily updates go to groups listed in **Telegram Groups**. Leave notifications and other direct messages require the employee or approver to open a direct chat with the bot first.

## Set up plain English requests

1. Open **Office Bot Settings → General** and enable **Understand Plain English**.
2. Choose a provider: **OpenRouter**, **OpenAI**, **Anthropic**, **Google Gemini**, or **Custom OpenAI-compatible**.
3. For a custom provider, enter its **API Base URL**. The other providers fill this in automatically.
4. Choose a model that supports tool calls. Select **Refresh Models** to reload the public model catalog. If a model is not listed, you can enter its model ID directly.
5. Enter the provider’s API key and save.

The model catalog is public and does not use the API key. The key is used when the bot sends a request to the selected provider. Keep the key private. Only models that the catalog identifies as supporting tool calls are listed; custom model IDs can still be entered manually and must support tool calls.

## Set up petty cash and Hive

### Petty cash

For monthly accounting, configure the following in **Office Bot Settings → General**:

- **Default Company**
- **Default Cash Account**
- An expense **Account** on every Petty Cash Category employees can select

The bot records petty cash usage as entries. On the first of each month, it creates a **draft** Journal Entry for the previous month. The entry debits each category’s expense account and credits the default cash account. Review and submit the draft in Frappe. Categories without an account are left out and logged for the administrator.

### Hive

For `/task`, add a row to **Hive Sites** in **Office Bot Settings → General**:

- **Label**: the name employees see
- **Site URL**: the remote Hive site URL
- **API Key** and **API Secret**: credentials for an account allowed to create Hive tasks, read projects and members, and assign tasks
- **Is Active**: enable this site for task creation

If more than one site is active, the bot asks which one to use. The selected site must have an open project. Check the Hive site URL and credentials if task creation fails.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| “Your user is not linked to an active Employee” | Ask HR to link your Frappe user to an active Employee. |
| Telegram ignores a group message | Confirm Telegram is enabled, the group chat ID is listed, and the message is a command, bot mention, or reply to the bot’s question. |
| Telegram says the user is unknown | Add the Telegram username or ID to **Telegram Users**, linked to the correct Frappe User. |
| Telegram direct notification does not arrive | The recipient must start a direct chat with the bot. Also check that Telegram is enabled and their user mapping is correct. |
| Telegram command menu is missing | Save the bot token and click **Connect Telegram**. The site must be reachable over HTTPS. |
| Leave cannot be applied | Check the employee’s leave allocation and leave approver. Ask HR to review Leave Application workflow settings. |
| WFH cannot be applied | Check for overlapping leave, another Attendance Request, marked attendance, or a holiday. |
| Plain English is not understood | Check that the feature is enabled, the provider key is valid, and the selected model supports tool calls. Try a slash command or `/help`. |
| No model appears in the list | Click **Refresh Models**. Check that the site can reach the public Models.dev catalog, or enter a model ID manually. |
| Hive task cannot be created | Check that an active Hive site and valid credentials are configured, and that the site has an open project. |
| Petty cash is missing from the monthly journal | Check the Default Company, Default Cash Account, and category accounts. Review Error Log for skipped categories. |

For errors that remain, ask a Frappe administrator to review **Error Log** and the site worker logs.
