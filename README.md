# 📡 Telegram → TRMNL Book Reader

This project lets you forward PDFs from **Telegram** directly to a **TRMNL** device display using a **Pipedream** integration.

It listens for incoming Telegram messages with PDF documents and captions, extracts the PDF content and formatting info (CSS classes and styles), then sends that to your TRMNL plugin.

![trmnl telegram ipad send to ](./telegram-trmnl.jpg)

---

## ✨ What It Does

1. You send a PDF document to a Telegram bot.
1. The bot grabs the PDF content and formats a payload:

   ```json
   {
     "merge_variables": {
       "file_url": "https://...",
       "file_type": "pdf",
       "file_action": "1" // pageNr if type=PDF
     }
   }
   ```
4. This will display the file with specific action on the device.

---

## 🚀 Setup Instructions

> ✅ Complete setup takes ~10–15 minutes

---

### 1. 🔌 Set Up Your TRMNL Plugin

1. Visit [usetrmnl.com](https://usetrmnl.com/)
2. Go to **Dashboard → Plugins**
3. Click **“+ Add Plugin”**
4. Choose **Custom Plugin** and create Private Plugin with Webhook.
5. Copy your plugin’s UUID which you'll need it later.
6. Setup Markup by copying the content of the [Markup.html](./markup/shared.html) (Can use it shared between different views)

---

### 2. 🤖 Create a Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. You'll receive a **Bot Token**, like:

   ```
   6119652656:AAxxxxx...
   ```

Save this for the Pipedream step.

---

### 3. ⚙️ Set Up the Pipedream Workflow

> You’ll use [Pipedream.com](https://pipedream.com) to glue it all together

#### Step A: Connect Telegram

1. Go to [Pipedream Telegram integrations](https://pipedream.com/apps/telegram_bot_api)
2. Click **“Connect Account”**
3. Paste your Telegram Bot Token when prompted

#### Step B: Import the Component

1. Create a **new workflow** in Pipedream
2. Choose **Trigger**: Telegram → New Message
3. Add a new **“Run Node.js Code”** step
4. Paste the code from 'src.js` (in this repo)
5. In the step config:
   - Select your Telegram bot
   - Set `plugin_id` to the TRMNL plugin UUID you copied earlier

#### Step C: Deploy

- Save and deploy the workflow
- Start sending PDFs to your bot!

---

## 🔐 Privacy & Security

- Telegram file links are temporary and not public
- You do **not** need to upload PDFs to third-party services
- No cloud PDF hosting needed — all via Telegram CDN

---

## 🛟 Need Help?

If you have issues setting up TRMNL, Telegram Bot, or Pipedream:

- Check the [TRMNL Docs](https://docs.usetrmnl.com/)
- Use [@BotFather](https://t.me/BotFather) to regenerate your token
- Visit [Pipedream Support](https://docs.pipedream.com/)
- We are also open to contributions and improvements! So feel free to open issues or PRs.

---

Made with 💻 by [Shahriar Yazdipour]

