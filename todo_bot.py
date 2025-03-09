import telebot
from telebot import types
from telebot_calendar import Calendar, CallbackData, ENGLISH_LANGUAGE
import datetime
import threading
import time
import traceback  # Thêm import này ở đầu file

token = '7594590300:AAHc7ytdo9ONdb3rhYyYqkRkDHHlN1KwH3Q'  # Replace with your real bot token from @BotFather
bot = telebot.TeleBot(token)
calendar = Calendar(language=ENGLISH_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')
now = datetime.datetime.now()
# a dictionary that stores all tasks
todos = {}

# Thêm biến để lưu thông tin tạm thời cho quá trình thêm task
user_task_info = {}

# bot start and button output
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(True)
    button1 = types.KeyboardButton('✅ Thêm việc')
    button2 = types.KeyboardButton('Xem danh sách')
    button3 = types.KeyboardButton('Thống kê')
    button4 = types.KeyboardButton('Trợ giúp')
    keyboard.add(button1)
    keyboard.add(button2)
    keyboard.add(button3)
    keyboard.add(button4)
    bot.send_message(message.chat.id, 'Xin chào, ' + message.from_user.first_name + '!', reply_markup=keyboard)


@bot.message_handler(commands=['help'])
def hepling(message):
    bot.send_message(message.chat.id, '''
⏰ Thêm nhắc nhở để bạn không quên những việc quan trọng
''')

# task deletion function
def delete_task(chat_id, c_date, task):
    if todos.get(chat_id) is not None:
        if todos[chat_id].get(c_date) is not None:
            todos[chat_id][c_date].remove(task)
            if len(todos[chat_id][c_date]) == 0:
                del todos[chat_id][c_date]
            if len(todos[chat_id]) == 0:
                del todos[chat_id]

# Hàm hiển thị thống kê - định nghĩa trước khi được gọi
def show_statistics(chat_id):
    if not todos.get(chat_id):
        bot.send_message(chat_id, 'Không có dữ liệu công việc để thống kê')
        return
    
    # Thống kê tổng quát
    total_tasks = 0
    completed_tasks = 0
    today_tasks = 0
    today_completed = 0
    upcoming_tasks = 0
    overdue_tasks = 0
    
    today_date = datetime.datetime.now().strftime("%d.%m.%Y")
    
    for date, tasks in todos[chat_id].items():
        for task in tasks:
            total_tasks += 1
            if task.get('completed', False):
                completed_tasks += 1
            
            # Kiểm tra công việc hôm nay
            if date == today_date:
                today_tasks += 1
                if task.get('completed', False):
                    today_completed += 1
            
            # Kiểm tra công việc sắp tới và quá hạn
            try:
                task_date = datetime.datetime.strptime(date, "%d.%m.%Y").date()
                current_date = datetime.datetime.now().date()
                
                if task_date > current_date:
                    upcoming_tasks += 1
                elif task_date < current_date and not task.get('completed', False):
                    overdue_tasks += 1
            except ValueError:
                continue
    
    # Tính tỷ lệ hoàn thành
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    today_completion_rate = (today_completed / today_tasks * 100) if today_tasks > 0 else 0
    
    # Tạo thông báo thống kê
    stats_text = (
        f"📊 THỐNG KÊ CÔNG VIỆC 📊\n\n"
        f"📝 Tổng số công việc: {total_tasks}\n"
        f"✅ Đã hoàn thành: {completed_tasks} ({completion_rate:.1f}%)\n"
        f"⏳ Chưa hoàn thành: {total_tasks - completed_tasks}\n\n"
        
        f"📅 CÔNG VIỆC HÔM NAY ({today_date}):\n"
        f"📝 Tổng số: {today_tasks}\n"
        f"✅ Đã hoàn thành: {today_completed} ({today_completion_rate:.1f}%)\n"
        f"⏳ Chưa hoàn thành: {today_tasks - today_completed}\n\n"
        
        f"⏰ CÔNG VIỆC SẮP TỚI: {upcoming_tasks}\n"
        f"⚠️ CÔNG VIỆC QUÁ HẠN: {overdue_tasks}\n"
    )
    
    # Thêm thống kê theo ngày
    stats_text += "\n📅 THỐNG KÊ THEO NGÀY:\n"
    for date, tasks in sorted(todos[chat_id].items()):
        completed_count = sum(1 for task in tasks if task.get('completed', False))
        stats_text += f"- {date}: {completed_count}/{len(tasks)} hoàn thành\n"
    
    # Gửi thông báo thống kê
    bot.send_message(chat_id, stats_text)

@bot.message_handler(content_types=['text'])
def call(message):
    if message.text == '✅ Thêm việc':
        bot.send_message(message.chat.id, 'Bạn muốn thêm việc vào ngày nào?', reply_markup=calendar.create_calendar(
            name=calendar_1.prefix,
            year=now.year,
            month=now.month)
                         )
    elif message.text == 'Xem danh sách':
        if not todos.get(message.chat.id):
            bot.send_message(message.chat.id, 'Không có việc cần làm')
        else:
            for chat_id, dates in todos.items():
                if chat_id == message.chat.id:
                    for date, tasks in dates.items():
                        # Tạo tin nhắn mới cho mỗi ngày
                        tasks_text = ''
                        for task in tasks:
                            status = "✅ " if task.get('completed', False) else "⏳ "
                            tasks_text += f'{status}{task["task"]} (Từ {task["start_time"]} đến {task["end_time"]})\n'
                        
                        text = f'Công việc ngày {date}:\n{tasks_text}'
                        keyboard = types.InlineKeyboardMarkup(row_width=2)
                        
                        for task in tasks:
                            # Nút đánh dấu hoàn thành/chưa hoàn thành
                            if task.get('completed', False):
                                complete_button = types.InlineKeyboardButton(
                                    text=f'❌ Chưa hoàn thành: {task["task"]}',
                                    callback_data=f'mark_incomplete:{date}:{task["task"]}'
                                )
                            else:
                                complete_button = types.InlineKeyboardButton(
                                    text=f'✅ Đánh dấu hoàn thành: {task["task"]}',
                                    callback_data=f'mark_complete:{date}:{task["task"]}'
                                )
                            
                            # Nút sửa và xóa
                            edit_button = types.InlineKeyboardButton(
                                text=f'✏️ Sửa: {task["task"]}',
                                callback_data=f'edit:{date}:{task["task"]}'
                            )
                            delete_button = types.InlineKeyboardButton(
                                text=f'❌ Xóa: {task["task"]}',
                                callback_data=f'delete:{date}:{task["task"]}'
                            )
                            
                            keyboard.add(complete_button)
                            keyboard.add(edit_button, delete_button)
                        
                        bot.send_message(message.chat.id, text, reply_markup=keyboard)
    elif message.text == 'Thống kê':
        show_statistics(message.chat.id)
    elif message.text == 'Trợ giúp':
        bot.send_message(message.chat.id, '''
⏰ Thêm nhắc nhở để bạn không quên những việc quan trọng
''')
    else:
        bot.send_message(message.chat.id, "🙄 Tôi không hiểu... Hãy nhấn 'Thêm việc' trong menu")

# deletes the task and displays a message about the successful deletion of this task.
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete:'))
def delete_callback(call):
    _, date, task_name = call.data.split(':')
    chat_id = call.message.chat.id
    
    # Tìm và xóa task
    if chat_id in todos and date in todos[chat_id]:
        tasks = todos[chat_id][date]
        for task in tasks:
            if task['task'] == task_name:
                tasks.remove(task)
                if not tasks:  # Nếu không còn task nào trong ngày
                    del todos[chat_id][date]
                if not todos[chat_id]:  # Nếu không còn ngày nào có task
                    del todos[chat_id]
                bot.answer_callback_query(call.id, text=f'Đã xóa việc "{task_name}"')
                bot.delete_message(chat_id, call.message.message_id)
                return

# Xử lý nút sửa công việc
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit:'))
def edit_callback(call):
    _, date, task_name = call.data.split(':')
    chat_id = call.message.chat.id
    
    # Lưu thông tin task cần sửa
    if chat_id not in user_task_info:
        user_task_info[chat_id] = {}
    
    user_task_info[chat_id]['edit_mode'] = True
    user_task_info[chat_id]['old_date'] = date
    user_task_info[chat_id]['old_task'] = task_name
    
    # Tìm thông tin task cũ
    old_task = None
    if chat_id in todos and date in todos[chat_id]:
        for task in todos[chat_id][date]:
            if task['task'] == task_name:
                old_task = task
                break
    
    if old_task:
        # Hiển thị menu chọn thông tin cần sửa
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("1️⃣ Sửa ngày", callback_data="edit_option:date"),
            types.InlineKeyboardButton("2️⃣ Sửa giờ", callback_data="edit_option:time"),
            types.InlineKeyboardButton("3️⃣ Sửa nội dung công việc", callback_data="edit_option:task"),
            types.InlineKeyboardButton("❌ Hủy", callback_data="edit_option:cancel")
        )
        
        text = (f"Đang sửa công việc:\n"
                f"📝 {task_name}\n"
                f"📅 Ngày: {date}\n"
                f"⏰ Từ {old_task['start_time']} đến {old_task['end_time']}\n\n"
                f"Chọn thông tin bạn muốn sửa:")
        
        bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=keyboard)

# Xử lý lựa chọn sửa thông tin
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_option:'))
def edit_option_callback(call):
    option = call.data.split(':')[1]
    chat_id = call.message.chat.id
    
    if option == 'date':
        bot.edit_message_text(
            "Chọn ngày mới:",
            chat_id,
            call.message.message_id,
            reply_markup=calendar.create_calendar(
                name=calendar_1.prefix,
                year=now.year,
                month=now.month
            )
        )
    elif option == 'time':
        # Tạo keyboard cho việc chọn giờ bắt đầu mới
        keyboard = types.InlineKeyboardMarkup(row_width=4)
        hours = [str(i).zfill(2) for i in range(24)]
        hour_buttons = [types.InlineKeyboardButton(text=h, callback_data=f'start_hour:{h}') for h in hours]
        keyboard.add(*hour_buttons)
        
        bot.edit_message_text(
            "Chọn giờ bắt đầu mới:",
            chat_id,
            call.message.message_id,
            reply_markup=keyboard
        )
    elif option == 'task':
        msg = bot.send_message(chat_id, "Nhập nội dung công việc mới:")
        bot.register_next_step_handler(msg, update_task_content)
    elif option == 'cancel':
        bot.delete_message(chat_id, call.message.message_id)
        if chat_id in user_task_info:
            del user_task_info[chat_id]

def update_task_content(message):
    chat_id = message.chat.id
    if chat_id in user_task_info and user_task_info[chat_id].get('edit_mode'):
        old_date = user_task_info[chat_id]['old_date']
        old_task_name = user_task_info[chat_id]['old_task']
        new_content = message.text
        
        # Cập nhật nội dung công việc
        if chat_id in todos and old_date in todos[chat_id]:
            for task in todos[chat_id][old_date]:
                if task['task'] == old_task_name:
                    task['task'] = new_content
                    bot.send_message(
                        chat_id,
                        f"Đã cập nhật nội dung công việc thành:\n{new_content}"
                    )
                    break
        
        # Xóa thông tin tạm thời
        del user_task_info[chat_id]

# Cập nhật hàm add_task để hỗ trợ chế độ sửa
def add_task(message, chat_id, c_date, start_time, end_time):
    task = message.text
    
    # Kiểm tra xem đang trong chế độ sửa hay không
    if chat_id in user_task_info and user_task_info[chat_id].get('edit_mode'):
        old_date = user_task_info[chat_id]['old_date']
        old_task = user_task_info[chat_id]['old_task']
        
        # Xóa task cũ
        if chat_id in todos and old_date in todos[chat_id]:
            todos[chat_id][old_date] = [t for t in todos[chat_id][old_date] if t['task'] != old_task]
            if not todos[chat_id][old_date]:
                del todos[chat_id][old_date]
    
    # Thêm task mới hoặc task đã sửa
    new_task = {
        'task': task,
        'start_time': start_time,
        'end_time': end_time,
        'start_notified': False,  # Thông báo bắt đầu
        'end_notified': False,     # Thông báo kết thúc
        'completed': False  # Thêm trường completed
    }
    
    if todos.get(chat_id) is not None:
        if todos[chat_id].get(c_date) is not None:
            todos[chat_id][c_date].append(new_task)
        else:
            todos[chat_id][c_date] = [new_task]
    else:
        todos[chat_id] = {c_date: [new_task]}
    
    text = f'{"Đã cập nhật" if "edit_mode" in user_task_info.get(chat_id, {}) else "Đã thêm"} công việc thành công:\n"{task}"\nNgày: {c_date}\nTừ {start_time} đến {end_time}\n\n⚠️ Bạn sẽ nhận được thông báo:\n- 15 phút trước khi bắt đầu\n- 10 phút trước khi kết thúc'
    bot.send_message(chat_id=chat_id, text=text)
    
    # Xóa thông tin tạm thời
    if chat_id in user_task_info:
        del user_task_info[chat_id]

# Thêm decorator này để xử lý callback từ calendar
@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1.prefix))
def callback_inline(call: types.CallbackQuery):
    name, action, year, month, day = call.data.split(calendar_1.sep)
    date = calendar.calendar_query_handler(bot=bot, call=call, name=name, action=action, year=year, month=month,
                                           day=day)
    if action == 'DAY':
        c_date = date.strftime("%d.%m.%Y")
        user_task_info[call.from_user.id] = {'date': c_date}
        
        # Tạo keyboard cho việc chọn giờ bắt đầu
        keyboard = types.InlineKeyboardMarkup(row_width=4)
        hours = [str(i).zfill(2) for i in range(24)]
        hour_buttons = [types.InlineKeyboardButton(text=h, callback_data=f'start_hour:{h}') for h in hours]
        keyboard.add(*hour_buttons)
        
        bot.send_message(chat_id=call.from_user.id, 
                        text=f'Bạn đã chọn ngày {c_date}\nVui lòng chọn GIỜ BẮT ĐẦU:', 
                        reply_markup=keyboard)
    elif action == 'CANCEL':
        if call.from_user.id in user_task_info:
            del user_task_info[call.from_user.id]
        bot.send_message(chat_id=call.from_user.id, text='🚫 Đã hủy')

# Handler cho việc chọn giờ bắt đầu
@bot.callback_query_handler(func=lambda call: call.data.startswith('start_hour:'))
def process_start_hour(call):
    hour = call.data.split(':')[1]
    user_task_info[call.from_user.id]['start_hour'] = hour
    
    # Tạo keyboard cho việc chọn phút bắt đầu
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    minutes = ['00', '15', '30', '45']
    minute_buttons = [types.InlineKeyboardButton(text=m, callback_data=f'start_minute:{m}') for m in minutes]
    keyboard.add(*minute_buttons)
    
    bot.edit_message_text(chat_id=call.from_user.id,
                         message_id=call.message.message_id,
                         text=f'Đã chọn giờ bắt đầu: {hour}h\nVui lòng chọn PHÚT BẮT ĐẦU:',
                         reply_markup=keyboard)

# Handler cho việc chọn phút bắt đầu
@bot.callback_query_handler(func=lambda call: call.data.startswith('start_minute:'))
def process_start_minute(call):
    minute = call.data.split(':')[1]
    user_task_info[call.from_user.id]['start_minute'] = minute
    
    # Tạo keyboard cho việc chọn giờ kết thúc
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    hours = [str(i).zfill(2) for i in range(24)]
    hour_buttons = [types.InlineKeyboardButton(text=h, callback_data=f'end_hour:{h}') for h in hours]
    keyboard.add(*hour_buttons)
    
    start_time = f"{user_task_info[call.from_user.id]['start_hour']}:{minute}"
    bot.edit_message_text(chat_id=call.from_user.id,
                         message_id=call.message.message_id,
                         text=f'Đã chọn giờ bắt đầu: {start_time}\nVui lòng chọn GIỜ KẾT THÚC:',
                         reply_markup=keyboard)

# Handler cho việc chọn giờ kết thúc
@bot.callback_query_handler(func=lambda call: call.data.startswith('end_hour:'))
def process_end_hour(call):
    hour = call.data.split(':')[1]
    user_task_info[call.from_user.id]['end_hour'] = hour
    
    # Tạo keyboard cho việc chọn phút kết thúc
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    minutes = ['00', '15', '30', '45']
    minute_buttons = [types.InlineKeyboardButton(text=m, callback_data=f'end_minute:{m}') for m in minutes]
    keyboard.add(*minute_buttons)
    
    bot.edit_message_text(chat_id=call.from_user.id,
                         message_id=call.message.message_id,
                         text=f'Đã chọn giờ kết thúc: {hour}h\nVui lòng chọn PHÚT KẾT THÚC:',
                         reply_markup=keyboard)

# Handler cho việc chọn phút kết thúc
@bot.callback_query_handler(func=lambda call: call.data.startswith('end_minute:'))
def process_end_minute(call):
    minute = call.data.split(':')[1]
    user_info = user_task_info[call.from_user.id]
    end_time = f"{user_info['end_hour']}:{minute}"
    start_time = f"{user_info['start_hour']}:{user_info['start_minute']}"
    
    msg = bot.send_message(chat_id=call.from_user.id,
                          text=f'Thời gian đã chọn:\nNgày: {user_info["date"]}\n'
                               f'Từ: {start_time} đến {end_time}\n\n'
                               f'Vui lòng nhập công việc cần làm:')
    
    # Lưu thông tin thời gian vào user_info
    user_info['end_minute'] = minute
    user_info['start_time'] = start_time
    user_info['end_time'] = end_time
    
    bot.register_next_step_handler(msg, lambda message: add_task(message, 
                                                               chat_id=call.from_user.id,
                                                               c_date=user_info['date'],
                                                               start_time=start_time,
                                                               end_time=end_time))

def check_and_notify():
    while True:
        current_time = datetime.datetime.now()
        
        # Kiểm tra tất cả các công việc của mọi người dùng
        for chat_id, dates in todos.items():
            for date, tasks in dates.items():
                # Chuyển đổi date string thành datetime object
                try:
                    task_date = datetime.datetime.strptime(date, "%d.%m.%Y")
                except ValueError:
                    continue
                
                # Chỉ kiểm tra các task trong ngày hiện tại
                if task_date.date() == current_time.date():
                    for task in tasks:
                        try:
                            # Chuyển đổi thời gian bắt đầu thành datetime
                            start_time = datetime.datetime.strptime(f"{date} {task['start_time']}", "%d.%m.%Y %H:%M")
                            
                            # Chuyển đổi thời gian kết thúc thành datetime
                            end_time = datetime.datetime.strptime(f"{date} {task['end_time']}", "%d.%m.%Y %H:%M")
                            
                            # Tính thời gian thông báo bắt đầu (trước 15 phút)
                            start_notify_time = start_time - datetime.timedelta(minutes=15)
                            
                            # Tính thời gian thông báo kết thúc (trước 10 phút)
                            end_notify_time = end_time - datetime.timedelta(minutes=10)
                            
                            # Kiểm tra và gửi thông báo bắt đầu
                            if not task.get('start_notified', False) and \
                               current_time >= start_notify_time and \
                               current_time < start_time:
                                
                                # Gửi thông báo bắt đầu
                                notification_text = (
                                    f"⚠️ Nhắc nhở: Còn 15 phút nữa đến giờ bắt đầu công việc!\n\n"
                                    f"📝 Công việc: {task['task']}\n"
                                    f"🕐 Bắt đầu: {task['start_time']}\n"
                                    f"🕐 Kết thúc: {task['end_time']}"
                                )
                                bot.send_message(chat_id, notification_text)
                                
                                # Đánh dấu đã thông báo bắt đầu
                                task['start_notified'] = True
                            
                            # Kiểm tra và gửi thông báo kết thúc
                            if not task.get('end_notified', False) and \
                               current_time >= end_notify_time and \
                               current_time < end_time:
                                
                                # Gửi thông báo kết thúc
                                notification_text = (
                                    f"⏰ Nhắc nhở: Còn 10 phút nữa đến hạn hoàn thành công việc!\n\n"
                                    f"📝 Công việc: {task['task']}\n"
                                    f"🕐 Bắt đầu: {task['start_time']}\n"
                                    f"🕐 Kết thúc: {task['end_time']}\n\n"
                                    f"Hãy hoàn thành công việc của bạn!"
                                )
                                bot.send_message(chat_id, notification_text)
                                
                                # Đánh dấu đã thông báo kết thúc
                                task['end_notified'] = True
                                
                        except (ValueError, KeyError):
                            continue
        
        # Đợi 1 phút trước khi kiểm tra lại
        time.sleep(60)

# Khởi động thread kiểm tra thông báo khi bot chạy
def start_notification_thread():
    notification_thread = threading.Thread(target=check_and_notify, daemon=True)
    notification_thread.start()



# Sửa lại handler đánh dấu hoàn thành
@bot.callback_query_handler(func=lambda call: call.data.startswith('mark_complete:') or call.data.startswith('mark_incomplete:'))
def handle_task_completion(call):
    try:
        action = call.data.split(':')[0]
        parts = call.data.split(':')
        if len(parts) < 3:
            bot.answer_callback_query(call.id, text="Lỗi: Dữ liệu không hợp lệ")
            return
            
        date = parts[1]
        task_name = ':'.join(parts[2:])  # Ghép lại tên task nếu có dấu ':'
        chat_id = call.message.chat.id
        
        if chat_id not in todos or date not in todos[chat_id]:
            bot.answer_callback_query(call.id, text="Không tìm thấy công việc")
            return

        # Tìm và cập nhật trạng thái task
        for task in todos[chat_id][date]:
            if task['task'] == task_name:
                task['completed'] = (action == 'mark_complete')
                status_text = "hoàn thành" if action == 'mark_complete' else "chưa hoàn thành"
                bot.answer_callback_query(call.id, text=f'Đã đánh dấu {status_text}: "{task_name}"')
                
                # Cập nhật tin nhắn
                tasks_text = ''
                for t in todos[chat_id][date]:
                    status = "✅ " if t.get('completed', False) else "⏳ "
                    tasks_text += f'{status}{t["task"]} (Từ {t["start_time"]} đến {t["end_time"]})\n'
                
                text = f'Công việc ngày {date}:\n{tasks_text}'
                
                # Tạo keyboard mới
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                for t in todos[chat_id][date]:
                    # Nút đánh dấu hoàn thành/chưa hoàn thành
                    complete_button = types.InlineKeyboardButton(
                        text=f'❌ Chưa hoàn thành: {t["task"]}' if t.get('completed', False) else f'✅ Đánh dấu hoàn thành: {t["task"]}',
                        callback_data=f'mark_incomplete:{date}:{t["task"]}' if t.get('completed', False) else f'mark_complete:{date}:{t["task"]}'
                    )
                    
                    # Nút sửa và xóa
                    edit_button = types.InlineKeyboardButton(
                        text=f'✏️ Sửa: {t["task"]}',
                        callback_data=f'edit:{date}:{t["task"]}'
                    )
                    delete_button = types.InlineKeyboardButton(
                        text=f'❌ Xóa: {t["task"]}',
                        callback_data=f'delete:{date}:{t["task"]}'
                    )
                    
                    keyboard.add(complete_button)
                    keyboard.add(edit_button, delete_button)
                
                # Cập nhật tin nhắn với keyboard mới
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=text,
                    reply_markup=keyboard
                )
                return
                
        bot.answer_callback_query(call.id, text="Không tìm thấy công việc cần cập nhật")
        
    except Exception as e:
        print(f"Lỗi khi xử lý đánh dấu hoàn thành: {str(e)}")
        bot.answer_callback_query(call.id, text="Đã xảy ra lỗi khi cập nhật trạng thái")


# Thêm vào cuối file, trước bot.polling()
if __name__ == '__main__':
    start_notification_thread()
    bot.polling(none_stop=True)