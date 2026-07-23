import os
import telebot 
import sqlite3

# --- CONFIGURACIÓN DEL BOT ---
# Reemplaza 'llave' con el código que te dio el BotFather
TOKEN = 'llave'
bot = telebot.TeleBot(TOKEN)

# Constante de gestión
COMISION_GESTION = 0.20
# Diccionario para guardar los datos temporales de cada chat
user_data = {}

def format_ven(numero):
    """Formatea números al estilo venezolano: 1.250,00"""
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INICIO DEL BOT ---
@bot.message_handler(func=lambda message: message.text.lower() in ['/start','/vender'])

def iniciar(message):
    user_data[message.chat.id] = {}
    msg = bot.send_message(message.chat.id, "     **Joyas Inspiración**     \n\n  ¿Cuál es el nombre de la vendedora?")
    bot.register_next_step_handler(msg, proceso_tasa_bcv)

def proceso_tasa_bcv(message):
    user_data[message.chat.id]['name'] = message.text.capitalize()
    msg = bot.send_message(message.chat.id, " Ingrese la tasa BCV del día:")
    bot.register_next_step_handler(msg, proceso_tasa_paralelo)

def proceso_tasa_paralelo(message):
    try:
        user_data[message.chat.id]['bcv'] = float(message.text)
        msg = bot.send_message(message.chat.id, " Ingrese la tasa Paralelo (USDT):")
        bot.register_next_step_handler(msg, proceso_opcion_modo)
    except:
        msg = bot.reply_to(message, "❌ Error. Use solo números. Ingrese la tasa BCV de nuevo:")
        bot.register_next_step_handler(msg, proceso_tasa_bcv)

def proceso_opcion_modo(message):
    try:
        user_data[message.chat.id]['paralelo'] = float(message.text)
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add('1. Por piezas (Suma una a una)', '2. Monto total directamente')
        msg = bot.send_message(message.chat.id, "¿Cómo desea ingresar los datos?", reply_markup=markup)
        bot.register_next_step_handler(msg, proceso_datos_ventas)
    except:
        msg = bot.reply_to(message, "❌ Error. Ingrese la tasa Paralelo de nuevo:")
        bot.register_next_step_handler(msg, proceso_tasa_paralelo)

def proceso_datos_ventas(message):
    if '1' in message.text:
        user_data[message.chat.id]['total'] = 0
        user_data[message.chat.id]['piezas'] = 0
        msg = bot.send_message(message.chat.id, "Escriba el precio de la prenda. Cuando termine de Ingresar el costo de todas las prendas, escriba 'listo':", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, modo_detallado)
    else:
        msg = bot.send_message(message.chat.id, "¿Cuál es el monto total vendido ($)?", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, monto_total_rapido)

def modo_detallado(message):
    entrada = message.text.lower()
    if entrada == 'listo':
        finalizar_y_reportar(message)
    else:
        try:
            precio = float(entrada)
            user_data[message.chat.id]['total'] += precio
            user_data[message.chat.id]['piezas'] += 1
            msg = bot.send_message(message.chat.id, f" Registrado: {precio}$. (Escriba otro o 'listo')")
            bot.register_next_step_handler(msg, modo_detallado)
        except:
            msg = bot.send_message(message.chat.id, "❌ Ingrese un número o 'listo':")
            bot.register_next_step_handler(msg, modo_detallado)

def monto_total_rapido(message):
    try:
        user_data[message.chat.id]['total'] = float(message.text)
        msg = bot.send_message(message.chat.id, "¿Cuántas piezas se vendieron?")
        bot.register_next_step_handler(msg, finalizar_rapido)
    except:
        msg = bot.send_message(message.chat.id, "❌ Ingrese el monto total en números:")
        bot.register_next_step_handler(msg, monto_total_rapido)

def finalizar_rapido(message):
    try:
        user_data[message.chat.id]['piezas'] = int(message.text)
        finalizar_y_reportar(message)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Ingrese la cantidad de piezas en números:")
        bot.register_next_step_handler(msg, finalizar_rapido)

def finalizar_y_reportar(message):
    datos = user_data[message.chat.id]
    total = datos['total']
    piezas = datos['piezas']
    
    # Lógica de Escalas
    if piezas >= 25: porc = 0.30
    elif piezas >= 10: porc = 0.25
    elif piezas >= 1: porc = 0.20
    else: porc = 0
 
    #Pago en dolares 
    pago_v = total * porc
    monto_a_pagar = total - pago_v
    ganancia_g = total * COMISION_GESTION
    empresa = total - pago_v - ganancia_g
    
    # Conversión a Bolívares y aparalelo
    bs_bcv = total * datos['bcv']
    bs_paralelo = total * datos['paralelo']
    
    pago_bolivares_v = pago_v * datos['bcv']
    monto_a_pagar_B = monto_a_pagar * datos['bcv']
    ganancia_g_B =  ganancia_g * datos['bcv']
    
    #Reporte final y agregado la convercion a bolivares
    resumen = (
        f" **RESUMEN DE VENTAS**\n"
        f" **Vendedora:** {datos['name'.capitalize()]}\n"
        f"{'='*25}\n"
        f" Piezas: {piezas}\n"
        f" Venta Total: {total:.2f}$\n"
        f" Monto a pagar: {monto_a_pagar:.2f}$\n"
        f"{'='*25}\n"
        f"**Monto total vendido en bolivares:**\n"
        f"• Al BCV ({datos['bcv']}): {format_ven(bs_bcv)} Bs\n"
        f"• Al Paralelo ({datos['paralelo']}): {format_ven(bs_paralelo)} Bs\n"
        f"{'='*25}\n"
        f"**DEVOLUCION ($):**\n"
        f"• Ganancia  vendedora ({int(porc*100)}%): {pago_v:.2f}$\n"
        f"• Ganancia Coach (20%): {ganancia_g:.2f}$\n"
        f"• **Pagar a Empresa: {empresa:.2f}$**\n" 
        f"pago en bolivares: {monto_a_pagar_B}\n"
        f"Reporte Guardado"
    )

      
    
    bot.send_message(message.chat.id, resumen, parse_mode="Markdown")
    
    # Guardar en archivo TXT (esto se guardará en la PC donde corras el bot)
    with open("reporte_ventas_joyas.txt", "a", encoding="utf-8") as archivo:
        archivo.write(f"=" * 50)
        archivo.write("\n----------- REGISTRO ----------")
        archivo.write(f"\n------------VENDEDORA--------------\n")
        archivo.write(f"\n**Vendedora**({int(porc*100)}%): {datos['name'.capitalize()]}\n")
        archivo.write(f"\n**Venta total: {total:.2f}$**\n")
        archivo.write(f"\n**Piezas vendidas: {datos['piezas']}$**\n")
        archivo.write(f"\n** Ganancia:{ pago_v:.2f}$**\n")
        archivo.write(f"\n**Monto a pagar**:{monto_a_pagar:.2f}$\n")
        archivo.write(f"="* 50)
        archivo.write(f"\n------------COACH -----------\n")
        archivo.write(f"\n**Coach** (20%): {ganancia_g:.2f}$ \n")
        archivo.write(f"=" * 50)
        archivo.write(f"\n----------EMPRESA ---------\n")
        archivo.write(f"\n**Ganancia: {empresa:.2f}$**\n")
        
      
        
print(" Bot de Joyas Activo...")
bot.polling()