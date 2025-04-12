import logging
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


CAR_BRANDS = [
    'Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan', 'Volkswagen', 'Hyundai', 'Kia', 'Mercedes-Benz', 'BMW',
    'Audi', 'Peugeot', 'Fiat', 'Renault', 'Skoda', 'Mazda', 'Mitsubishi', 'Jeep', 'Subaru', 'Volvo'
]


CAR_EMISSIONS = {
    'Toyota': 0.192,
    'Honda': 0.185,
    'Ford': 0.198,
    'Chevrolet': 0.200,
    'Nissan': 0.188,
    'Volkswagen': 0.190,
    'Hyundai': 0.180,
    'Kia': 0.178,
    'Mercedes-Benz': 0.220,
    'BMW': 0.210,
    'Audi': 0.205,
    'Peugeot': 0.180,
    'Fiat': 0.170,
    'Renault': 0.160,
    'Skoda': 0.175,
    'Mazda': 0.182,
    'Mitsubishi': 0.195,
    'Jeep': 0.210,
    'Subaru': 0.200,
    'Volvo': 0.205
}

# Motorcycle emissions constant (in kg CO₂ per cc per km)
MOTORCYCLE_EMISSIONS = 0.02  # Adjust this as per average emission per cc

# Carbon emission calculation function
def calculate_car_emissions(brand, engine_size, km):
    emission_factor = CAR_EMISSIONS.get(brand, 0.2)  # Default emission factor for unknown brands
    return emission_factor * engine_size * km

def calculate_motorcycle_emissions(engine_size, km):
    return MOTORCYCLE_EMISSIONS * engine_size * km

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
    transport = context.user_data['transport']
    if transport == 'motorcycle':
        await update.message.reply_text("Enter the length of your ride in km:")
        return LENGTH
    else:
        await update.message.reply_text("Enter the length of your ride in km:")
        return LENGTH

async def length_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['length_km'] = float(update.message.text)
    transport = context.user_data['transport']
    engine = float(context.user_data.get('engine_size', 0))
    km = context.user_data['length_km']
    emissions = 0

    if transport == 'car':
        brand = context.user_data['brand']
        emissions = calculate_car_emissions(brand, engine, km)

    elif transport == 'motorcycle':
        emissions = calculate_motorcycle_emissions(engine, km)

    elif transport == 'train':
        emissions = 0.045 * km

    elif transport == 'plane':
        emissions = 0.15 * km

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
