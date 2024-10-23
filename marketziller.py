# Make Sure To Edit The Links In Lines 234 To 240!
# Make Sure To Also Edit Channel Ids, Chat Ids, & Wallet Addresses!
import logging
import qrcode
import io
import os
import asyncio
from datetime import datetime, timedelta
from telegram import InputFile
import base58
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ContextTypes # (pip install python-telegram-bot)
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler
from solana.rpc.api import Client
from solana.publickey import PublicKey # use solona version 0.18.0 (pip install solana==0.18.0)
import time

# Set up logging for the bot
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Your Bot Token and Solana Network Info
TOKEN = 'INSERT_BOT_TOKEN'
SOLANA_RPC_URL = 'https://api.mainnet-beta.solana.com'  # Use Solana mainnet RPC URL # DON"T CHANGE #
SOLANA_WALLET_ADDRESS = 'INSERT_WALLET_ADDRESS'
SOLANA_MINT_ADDRESS = 'So11111111111111111111111111111111111111112' # Change if you'd like to accept anything other than Solana as payment

# Initialize Solana Client
solana_client = Client(SOLANA_RPC_URL)

# Store Ads Info Temporarily
pending_ads = {}
user_images = {}


# Function to handle image upload
user_images = {}  # Dictionary to store images uploaded by users
IMAGE_FOLDER = "user_uploaded_images"

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# Command to start the image upload process
async def upload_image(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if update.message.chat.type != "private":
        await context.bot.send_message(chat_id=update.message.chat.id,
                                       text="Please send this command via direct message.")
        return
    else:
        await context.bot.send_message(chat_id=chat_id, text="Please upload your banner image for the ad.")

        # Set a flag to indicate we're expecting an image next
        context.user_data['expecting_image'] = True


# Function to include the image in the ad
# Function to handle receiving the image
async def handle_image(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    if context.user_data.get('expecting_image'):
        # Check if the user uploaded an image
        if update.message.photo:
            # Get the highest resolution image (last one in the list)
            photo_file = await update.message.photo[-1].get_file()

            # Create a file path to save the image locally
            image_path = os.path.join(IMAGE_FOLDER, f"{chat_id}_ad_image.png")

            # Download and save the image locally
            await photo_file.download_to_drive(image_path)

            # Save the image path in the user_images dictionary
            user_images[chat_id] = image_path

            # Confirm to the user that the image was received
            await context.bot.send_message(chat_id=chat_id, text="Image received! It will be used for your ad.")

            # Remove the flag indicating we're expecting an image
            context.user_data['expecting_image'] = False
        else:
            await context.bot.send_message(chat_id=chat_id, text="Please upload a valid image.")


# Define a list of promotion-related trigger words
PROMOTION_TRIGGERS = ["Who can I contact", "For marketing purposes", "Contact with marketing team", "Listing opportunites", "Listing opportunity"]

async def detect_promotional_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:  # Check if there's a message
        message_text = update.message.text.lower()  # Convert message to lowercase for easy matching

        # Check if the message contains any of the trigger words
        if any(trigger in message_text for trigger in PROMOTION_TRIGGERS):
            # If a promotional message is detected, send the response
            await context.bot.send_message(chat_id=update.message.chat_id,
                                           text="Please DM privately for marketing inquiries.")


# Function to generate the payment QR code and send it to the user
def generate_qr_code(data: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Save the QR code in memory
    img = qr.make_image(fill="blue", back_color="white")
    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)  # Rewind the file pointer to the beginning

    return byte_io


# Function to handle the transaction and generate the QR code
async def handle_transaction(update: Update, context: CallbackContext):
    chat_id = update.callback_query.message.chat.id

    # Create the transaction URL for the QR code (adjust values for Solana wallet and token)
    transaction_url = f"solana:{SOLANA_WALLET_ADDRESS}?amount=0.25&spl-token={SOLANA_MINT_ADDRESS}"

    # Generate the QR code image
    qr_code_image = generate_qr_code(transaction_url)

    # Send the QR code to the user
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=InputFile(qr_code_image, filename="transaction_qr.png"),
        caption="Scan this QR code with your Solana wallet app to complete the transaction."
    )


# Other functions (validate_wallet_address, error_handler, check_solana_payment, etc.)

async def start_bot(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if update.message.chat.type != "private":
        await context.bot.send_message(chat_id=update.message.chat.id,
                                       text="Please send this command via direct message.")
        return
    else:
        welcomeMessage = ("Welcome to the Marketziller Bot!\n\n"
                          "You may place an ad for your cryptocoin, community, website, and more here!\n"
                          "Tap the button below: \n"
                          )

        keyboard = [
            [
                InlineKeyboardButton("Tap to begin process", callback_data="submit_ad")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=welcomeMessage, reply_markup=reply_markup)


def validate_wallet_address(address):
    try:
        public_key = PublicKey(address)
        print(f"Valid Solana wallet address: {public_key}")
        return True
    except Exception as e:
        print(f"Invalid wallet address: {e}")
        return False

# Make Sure your wallet address is valid #
wallet_address = "INSERT_WALLET_ADDRESS"
validate_wallet_address(wallet_address)


# Define an error handler function
async def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# Start Bot
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()


# Command to Submit Project
async def submit_ad(update: Update, context: CallbackContext):
    chat_id = update.callback_query.message.chat.id
    if update.callback_query.message.chat.type != "private":
        await context.bot.send_message(chat_id=update.message.chat.id,
                                       text="Please direct message me to submit your ad.")
        return
    msg = "Please provide the project name and the link to the Telegram channel (separated by a space)."
    await context.bot.send_message(chat_id=chat_id, text=msg)


async def process_ad_submission(update: Update, context: CallbackContext):
    if update.message.chat.type != 'private':
        # Ignore group messages
        return
    chat_id = update.message.chat_id
    user_message = update.message.text.strip().split(" ", 1)

    # If the user uploaded an image, include it in the ad
    if 'ad_image' in context.user_data:
        await context.bot.send_photo(
            chat_id="INSERT_CHAT_ID",
            photo=InputFile(context.user_data['ad_image'], filename="ad_banner.png"),
            caption="."
        )
    else:
        # Send the ad without the image if no image was uploaded
        await context.bot.send_message(
            chat_id="INSERT_CHAT_ID",
            text="."
        )

    # Clear the uploaded image after the ad is posted
    context.user_data.pop('ad_image', None)


    if len(user_message) != 2:
        await context.bot.send_message(chat_id=chat_id,
                                       text="Invalid input. Please provide both project name and Telegram link.")
        return

    project_name, telegram_link = user_message
    pending_ads[chat_id] = {"project_name": project_name, "telegram_link": telegram_link}

    # Solana Wallet Payment URLs with deep linking
    solflare_app_url = "solflare://wallet/send?recipient=YOUR_WALLET_ADDRESS&amount=0.25&token=So11111111111111111111111111111111111111112"
    solflare_web_url = "https://solflare.com/send?recipient=YOUR_WALLET_ADDRESS&amount=0.25&token=So11111111111111111111111111111111111111112"

    phantom_app_url = "phantom://app/ul/v1/pay?recipient=YOUR_WALLET_ADDRESS&amount=0.25&spl-token=So11111111111111111111111111111111111111112"
    phantom_web_url = "https://phantom.app/ul/v1/pay?recipient=YOUR_WALLET_ADDRESS&amount=0.25&spl-token=So11111111111111111111111111111111111111112"

    sollet_web_url = "https://www.sollet.io/pay?recipient=YOUR_WALLET_ADDRESS&amount=0.25&spl-token=So11111111111111111111111111111111111111112"

    # Create an inline keyboard with wallet options (first tries app, then web)
    keyboard = [
        [
            #InlineKeyboardButton("Pay with Solflare (App)", url=solflare_app_url),
            InlineKeyboardButton("Pay with Solflare (Web)", url=solflare_web_url)
        ],
        [
            #InlineKeyboardButton("Pay with Phantom (App)", url=phantom_app_url),
            InlineKeyboardButton("Pay with Phantom (Web)", url=phantom_web_url)
        ],
        [InlineKeyboardButton("Pay with Sollet", url=sollet_web_url)],
    ]
    keyboard.append([InlineKeyboardButton("Generate QR Code", callback_data='generate_qr')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (f"Project: {project_name}\nLink: {telegram_link}\n\n"
           "Please make a payment of **0.25 SOLANA** to the following wallet address:\n"
           f"{SOLANA_WALLET_ADDRESS}\n\n"
           "You can complete the payment by selecting one of the wallet options below:")

    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    pending_ads[chat_id] = {"project_name": project_name, "telegram_link": telegram_link}

async def view_ads(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if update.message.chat.type != "private":
        await context.bot.send_message(chat_id=update.message.chat.id,
                                       text="Please send this command via direct message.")
        return
    else:
        if not pending_ads:
            await context.bot.send_message(chat_id=chat_id, text="No ads available.")
            return

        ads_message = "Here are the current ads:\n\n"
        for ad in pending_ads.values():
            ads_message += f"**Project:** {ad['project_name']}\n**Link:** {ad['telegram_link']}\n\n"

        await context.bot.send_message(chat_id=chat_id, text=ads_message, parse_mode=ParseMode.MARKDOWN)


async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    if query.data == 'generate_qr':
        # Call your existing QR code generation function with correct chat_id
        await handle_transaction(update, context)
    elif query.data == 'submit_ad':
        # Call existing submit_ad function
        await submit_ad(update, context)


# Function to Check Solana Payment

async def check_payment_by_signature(transaction_signature: str) -> bool:
    try:
        # Fetch transaction details using the signature
        tx_details = solana_client.get_confirmed_transaction(transaction_signature)

        # Check if the transaction was confirmed
        if 'result' in tx_details and tx_details['result']:
            # Check for errors in the transaction
            if tx_details['result']['meta']['err'] is None:
                print(f"Transaction {transaction_signature} was successful.")
                return True
            else:
                print(f"Transaction {transaction_signature} failed: {tx_details['result']['meta']['err']}")
                return False
        else:
            print("Transaction not found or not confirmed.")
            return False
    except Exception as e:
        logging.error(f"Error checking payment by signature: {str(e)}")
        return False

def is_valid_signature(signature: str) -> bool:
    # Check if the length is 88 characters and if all characters are valid Base58
    if len(signature) != 88:
        return False
    try:
        # Try decoding it as Base58
        base58.b58decode(signature)
        return True
    except ValueError:
        return False


# Define a dictionary to store active ads and their expiration time
active_ads= {}
async def send_reminder_messages(chat_id, ad_message, context):
    # Retrieve ad details from pending_ads or a similar dictionary
    ad_details = pending_ads.get(chat_id)

    if not ad_details:
        await context.bot.send_message(chat_id=chat_id, text="No ad information found for reminders.")
        return

    project_name = ad_details["project_name"]
    telegram_link = ad_details["telegram_link"]

    keyboard = [
        [
            InlineKeyboardButton(text=project_name, url=telegram_link)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    while datetime.now() < active_ads[chat_id]:
        for channel_id in ['INSERT_CHANNEL_ID', 'INSERT_CHANNEL_ID']:  # Same channel list where the ad was posted
            # Send the reminder message with the inline button to the channel
            await context.bot.send_message(
                chat_id=channel_id,  # Ensure this is the channel ID
                text=f"Reminder:\n{ad_message}\n Link: {telegram_link}",
                reply_markup=reply_markup,  # Attach the inline button here
                parse_mode=ParseMode.MARKDOWN
            )
        await asyncio.sleep(25 * 60)  # Wait 25 minutes before sending the next reminder


async def remove_ad_after_duration(chat_id, context):
    # Wait for 24 hours
    await asyncio.sleep(24 * 60 * 60)
    # Remove the ad after 24 hours
    if chat_id in active_ads:
        del active_ads[chat_id]
        await context.bot.send_message(chat_id=chat_id, text="Your ad has expired after 24 hours.")

async def post_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    image_path = user_images.get(chat_id)

    if update.message.chat.type != "private":
        await context.bot.send_message(chat_id=update.message.chat.id,
                                       text="Please send this command via direct message.")
        return
    else:
        # Check if there are enough arguments
        if not context.args:
            await context.bot.send_message(chat_id=chat_id, text="Please provide the transaction signature.")
            return

        transaction_signature = context.args[0]  # Get the transaction signature from the user input

        logging.info(f"Checking payment status for chat ID {chat_id} with transaction signature {transaction_signature}")

        if not is_valid_signature(transaction_signature):
            await context.bot.send_message(chat_id=chat_id, text="Invalid transaction signature format. Please try again.")
            return

        if await check_payment_by_signature(transaction_signature):  # Check if payment is valid
            await context.bot.send_message(chat_id=chat_id, text="Payment successful! Your ad will be posted.")

            # Retrieve ad details from pending_ads
            ad_details = pending_ads.get(chat_id)
            if not ad_details:
                await context.bot.send_message(chat_id=chat_id, text="No ad information found.")
                return

            project_name = ad_details["project_name"]
            telegram_link = ad_details["telegram_link"]

            # Customize the ad message to be posted
            ad_message = f"🚀 *{project_name}* 🚀\nCheck out their Telegram channel here: {telegram_link}"
            keyboard = [
                [
                    InlineKeyboardButton(text=project_name, url=telegram_link)
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=chat_id, text=ad_message, reply_markup=reply_markup)


            # List of channels where the ad will be posted
            channel_ids = ["INSERT_CHANNEL_IDS", "INSERT CHANNEL IDS"]  # Add the channel IDs here

            for channel_id in channel_ids:
                if image_path:
                    # If an image was uploaded, include it in the ad
                    await context.bot.send_photo(chat_id=channel_id, photo=open(image_path, 'rb'),
                                                 caption=f"{ad_message}\n")
                    await context.bot.send_message(chat_id=chat_id, text=ad_message, reply_markup=reply_markup)
                else:
                    # Post the ad without an image if no image was uploaded
                    await context.bot.send_message(chat_id=channel_id, text=f"{ad_message}\n")
                    await context.bot.send_message(chat_id=chat_id, text=ad_message, reply_markup=reply_markup)
               # await context.bot.send_message(chat_id=channel_id, text=ad_message, parse_mode=ParseMode.MARKDOWN)
            # Schedule reminder messages
            asyncio.create_task(send_reminder_messages(chat_id, ad_message, context))

            # Set ad expiration time (24 hours)
            expiration_time = datetime.now() + timedelta(hours=24)
            active_ads[chat_id] = expiration_time

            # Clear the pending ad after posting
            pending_ads.pop(chat_id, None)

            # Schedule ad removal after 24 hours
            asyncio.create_task(remove_ad_after_duration(chat_id, context))
        else:
            await context.bot.send_message(chat_id=chat_id, text="Payment not confirmed. Please check your transaction.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the message is a direct message (i.e., not from a group)
    if update.message.chat.type == "private":
        # Handle direct messages
        await context.bot.send_message(chat_id=update.message.chat.id, text="Welcome! Send me your ad details or type /start to begin.")
    else:
        # Check for promotional content in group/supergroup chats
        if update.message.chat.type == 'group' or update.message.chat.type == 'supergroup':
            await detect_promotional_message(update, context)

        # Ignore group messages unless they are commands
        return

async def check_transaction_status(transaction_signature):
    try:
        # Fetch transaction details
        transaction_details = await solana_client.get_transaction(transaction_signature)
        methods = await solana_client.get_supported_methods()
        print(methods)

        # Check if the transaction is confirmed
        if transaction_details and transaction_details['meta']['err'] is None:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking transaction status: {str(e)}")
        return False


# Handlers
# application.add_handler(CommandHandler('submit_ad', submit_ad))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_ad_submission))
application.add_handler(CommandHandler('post_ad', post_ad))
application.add_handler(CommandHandler('start_bot', start_bot))
# application.add_handler(CommandHandler('generate_qr', handle_transaction))
application.add_handler(CommandHandler('view_ads', view_ads))
application.add_handler(CommandHandler('upload_image', upload_image))
application.add_handler(MessageHandler(filters.PHOTO, handle_image))
application.add_handler(CallbackQueryHandler(button_handler))


# Add the error handler at the end
application.add_error_handler(error_handler)

# Start the Bot
application.run_polling()