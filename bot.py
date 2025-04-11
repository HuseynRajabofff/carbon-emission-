import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states
TRANSPORT, BRAND, ENGINE, LENGTH = range(4)

# Car brands (expand as needed)
CAR_BRANDS = [
    'Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan', 'Volkswagen', 'Hyundai', 'Kia', 'Mercedes-Benz', 'BMW',
    'Audi', 'Peugeot', 'Fiat', 'Renault', 'Skoda', 'Mazda', 'Mitsubishi', 'Jeep', 'Subaru', 'Volvo'
]

# Carbon Interface API config
CARBON_API_KEY = "ipubOmKpjgYbU4OahdZw"
CARBON_API_URL = "https://www.carboninterface.com/api/v1/estimates"
HEADERS = {
    "Authorization": f"Bearer {CARBON_API_KEY}",
    "Content-Type": "application/json"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Plane", callback_data='plane')],
        [InlineKeyboardButton("Train", callback_data='train')],
        [InlineKeyboardButton("Car", callback_data='car')],
        [InlineKeyboardButton("Motorcycle", callback_data='motorcycle')],
        [InlineKeyboardButton("Bicycle", callback_data='bicycle')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome! I'm your bot to calculate travel CO₂ waste. Choose your mode of transport:",
        reply_markup=reply_markup
    )
    return TRANSPORT

async def transport_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    transport = query.data
    context.user_data['transport'] = transport

    if transport == 'car':
        keyboard = [[InlineKeyboardButton(brand, callback_data=brand)] for brand in CAR_BRANDS[:10]] + \
                  [[InlineKeyboardButton(brand, callback_data=brand)] for brand in CAR_BRANDS[10:]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose your car brand:", reply_markup=reply_markup)
        return BRAND

    elif transport == 'motorcycle':
        await query.edit_message_text("Enter your engine size in cc (e.g. 500):")
        return ENGINE

    elif transport == 'bicycle':
        await query.edit_message_text("Enter the length of your ride in km:")
        return LENGTH

    else:
        await query.edit_message_text("Enter the length of your ride in km:")
        return LENGTH

async def brand_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['brand'] = query.data
    await query.edit_message_text("Enter your engine size in liters (e.g. 2.0):")
    return ENGINE

async def engine_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['engine_size'] = update.message.text
    await update.message.reply_text("Enter the length of your ride in km:")
    return LENGTH

async def length_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['length_km'] = float(update.message.text)
    transport = context.user_data['transport']
    engine = float(context.user_data.get('engine_size', 0))
    km = context.user_data['length_km']
    emissions = 0

    if transport == 'car':
        payload = {
            "type": "vehicle",
            "distance_unit": "km",
            "distance_value": km,
            "vehicle_model_id": "vehicle_model:car",
            "engine_size": engine,
            "fuel_source": "gasoline"  # this could be dynamic
        }
        try:
            response = requests.post(CARBON_API_URL, headers=HEADERS, json=payload)
            response.raise_for_status()
            emissions = response.json()['data']['attributes']['carbon_kg']
        except Exception as e:
            logger.error(f"API error: {e}")
            await update.message.reply_text("Something went wrong while calculating emissions. Showing estimate instead.")
            emissions = engine * 2.3 * km

    elif transport == 'motorcycle':
        emissions = engine * 0.02 * km
    elif transport == 'train':
        emissions = 0.045 * km
    elif transport == 'plane':
        emissions = 0.15 * km
    else:
        emissions = 0

    result = f"Your estimated CO₂ emission is {emissions:.2f} kg."
    if emissions < 1:
        result += " 🚴 Very eco-friendly!"
    elif emissions < 10:
        result += " 🟢 Eco-conscious travel."
    elif emissions < 50:
        result += " 🟡 Moderate emissions."
    else:
        result += " 🔴 Consider more sustainable options."

    await update.message.reply_text(result)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Calculation cancelled.")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token("8025705820:AAGfxtTnv2TT5zxnjkFkgNiJv1r45RcDKtk").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TRANSPORT: [CallbackQueryHandler(transport_chosen)],
            BRAND: [CallbackQueryHandler(brand_chosen)],
            ENGINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, engine_entered)],
            LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, length_entered)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()
