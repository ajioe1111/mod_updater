import os
import tkinter as tk
from tkinter import ttk, filedialog
import zipfile
import paramiko
import threading
import time
import webbrowser
import SSH

# Параметры подключения к серверу SSH (замените их на ваши)
ssh_host = SSH.ssh_host
ssh_port = SSH.ssh_port
ssh_username = SSH.ssh_username
ssh_password = SSH.ssh_password

# Путь к zip-файлу на сервере
ssh_remote_file_path = '/home/fuuka/mods_updater/mods.zip'

# Папка, где находятся текущие моды пользователя
user_mods_folder = ""

# Папка на сервере, где лежат моды в формате .jar
server_mods_folder = '/home/fuuka/mods_list'


def download_mods(destination_folder):
    try:
        # Устанавливаем SSH-соединение для скачивания файла
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ssh_host, ssh_port, ssh_username, ssh_password)

        # Осуществляем скачивание файла с сервера
        sftp = ssh_client.open_sftp()
        remote_file_path = ssh_remote_file_path
        local_file_path = os.path.join(destination_folder, 'mods.zip')

        # Получаем размер файла на сервере
        file_size = sftp.stat(remote_file_path).st_size

        # Определение времени начала загрузки
        start_time = time.time()

        # Оповещаем об успешной загрузке
        update_speed_label(0)  # Устанавливаем прогресс загрузки в 0
        update_progress_bar(0)  # Устанавливаем прогресс-бар в 0%
        progress_bar.grid()  # Отображаем элемент прогресса

        # Скачивание файла
        sftp.get(remote_file_path, local_file_path)

        # Закрываем SSH-соединение
        sftp.close()
        ssh_client.close()

        # Распаковываем скачанный zip-файл
        with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
            total_files = len(zip_ref.namelist())
            current_file = 0

            for file in zip_ref.namelist():
                current_file += 1
                percent = (current_file / total_files) * 100
                update_progress_bar(percent)  # Обновляем прогресс-бар

                # Распаковываем в папку назначения
                zip_ref.extract(file, destination_folder)

                # Измеряем прошедшее время и обновляем прогресс
                elapsed_time = time.time() - start_time
                current_bytes = os.path.getsize(local_file_path)
                speed = current_bytes / (1024 * elapsed_time)  # КБ в секунду
                update_speed_label(speed)

        # Удаляем временные файлы
        os.remove(local_file_path)

        # Оповещаем об успешном обновлении
        label.config(text="Моды успешно скачаны",
                     font=("Helvetica", 12), foreground="green")

    except Exception as e:
        # Если возникла ошибка, выводим сообщение
        label.config(text="Произошла ошибка при скачивании и обновлении модов", font=(
            "Helvetica", 12), foreground="red")
        print(f"Ошибка при скачивании и обновлении модов: {str(e)}")


def update_speed_label(speed):
    speed_label.config(text=f"Скорость загрузки: {speed:.2f} КБ/с")
    root.update()  # Обновляем интерфейс


def update_progress_bar(value):
    progress_bar["value"] = value
    root.update()  # Обновляем интерфейс


def update_mods():
    # Запрашиваем папку для сохранения модов
    destination_folder = filedialog.askdirectory(
        title="Выберите папку для сохранения модов")

    # Если пользователь не выбрал папку, выходим
    if not destination_folder:
        return

    # Скрываем элементы перед началом загрузки
    update_button["state"] = "disabled"
    label.config(text="Загрузка модов...", font=("Helvetica", 12))
    speed_label.grid()  # Отображаем элемент скорости загрузки
    progress_bar.grid()  # Отображаем прогресс-бар

    # Создаем и запускаем отдельный поток для загрузки модов
    download_thread = threading.Thread(
        target=download_mods, args=(destination_folder,))
    download_thread.start()


def update_user_mods():
    # Запрашиваем папку с модами пользователя
    destination_folder = filedialog.askdirectory(
        title="Выберите папку с модами пользователя")

    # Если пользователь не выбрал папку, выходим
    if not destination_folder:
        return

    try:
        # Устанавливаем SSH-соединение для доступа к серверу
        print("Connecting to SSH...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ssh_host, ssh_port, ssh_username, ssh_password)

        # Осуществляем подключение к SFTP
        print("Connecting to SFTP...")
        sftp = ssh_client.open_sftp()

        # Получаем список файлов .jar на сервере
        server_mods_list = [file for file in sftp.listdir(
            server_mods_folder) if file.endswith('.jar')]
        print("Server mods list:", server_mods_list)

        # Получаем список файлов .jar у пользователя
        user_mods_list = [file for file in os.listdir(
            destination_folder) if file.endswith('.jar')]
        print("User mods list:", user_mods_list)

        # Сравниваем списки и обновляем моды пользователя
        mods_to_download = list(set(server_mods_list) - set(user_mods_list))
        mods_to_delete = list(set(user_mods_list) - set(server_mods_list))

        print("Mods to download:", mods_to_download)
        print("Mods to delete:", mods_to_delete)

        # Скачиваем недостающие моды
        i = 0
        while i < len(mods_to_download):
            mod = mods_to_download[i]
            print(f"Downloading mod: {mod}")
            remote_path = os.path.join(server_mods_folder, mod)
            local_path = os.path.join(destination_folder, mod)
            time.sleep(1)

            try:
                sftp.get(remote_path, local_path)
                user_mods_list.append(mod)
                i += 1
            except FileNotFoundError:
                # Пишем в консоль какого мода нету
                print(f"Mod not found: {mod}")
                i += 1

            # После каждой итерации обновим списки
            server_mods_list = [file for file in sftp.listdir(
                server_mods_folder) if file.endswith('.jar')]
            user_mods_list = [file for file in os.listdir(
                destination_folder) if file.endswith('.jar')]

        # Удаляем лишние моды
        for mod in mods_to_delete:
            print(f"Deleting mod: {mod}")
            os.remove(os.path.join(destination_folder, mod))

        print("Update completed successfully.")

        # Закрываем SSH-соединение
        sftp.close()
        ssh_client.close()

        label.config(text="Моды успешно обновлены",
                     font=("Helvetica", 12), foreground="green")
    except FileNotFoundError as e:
        print(f"У пользователя не хватает файлов: {str(e)}")
        label.config(text="Моды успешно обновлены",
                     font=("Helvetica", 12), foreground="green")
    except Exception as e:
        label.config(text="Произошла неизвестная ошибка при обновлении модов пользователя", font=(
            "Helvetica", 12), foreground="red")
        print(
            f"Неизвестная ошибка при обновлении модов пользователя: {str(e)}")


def download_forge():
    try:
        # Устанавливаем SSH-соединение для скачивания файла
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ssh_host, ssh_port, ssh_username, ssh_password)

        # Осуществляем скачивание файла с сервера
        sftp = ssh_client.open_sftp()
        forge_remote_file_path = '/home/fuuka/forge_update/forge-installer.jar'
        forge_local_file_path = os.path.join(
            user_mods_folder, 'forge-installer.jar')

        sftp.get(forge_remote_file_path,
                 forge_local_file_path)  # Скачиваем файл

        # Закрываем SSH-соединение
        sftp.close()
        ssh_client.close()

        # Оповещаем об успешной загрузке
        webbrowser.open(forge_local_file_path)  # Открываем файл в браузере
        label.config(text="Forge успешно скачан и открыт",
                     font=("Helvetica", 12), foreground="green")

    except Exception as e:
        # Если возникла ошибка, выводим сообщение
        label.config(text="Произошла ошибка при скачивании и открытии Forge", font=(
            "Helvetica", 12), foreground="red")
        print(f"Ошибка при скачивании и открытии Forge: {str(e)}")


# Создаем окно приложения
root = tk.Tk()
root.title("Мод-апдейтер By Fuuka")
root.geometry("400x200")

# Создаем и настраиваем элементы интерфейса
frame = ttk.Frame(root)
frame.grid(column=0, row=0, padx=10, pady=10)

label = ttk.Label(frame, text="Жмякни на кнопочку", font=("Helvetica", 12))
label.grid(column=0, row=0, padx=5, pady=5, sticky="w")

update_button = ttk.Button(
    frame, text="Скачать весь набор", command=update_mods)
update_button.grid(column=0, row=1, padx=5, pady=5, sticky="w")

update_user_button = ttk.Button(
    frame, text="Обновить моды", command=update_user_mods)
update_user_button.grid(column=0, row=2, padx=5, pady=5, sticky="w")

speed_label = ttk.Label(frame, text="", font=("Helvetica", 10))
speed_label.grid(column=0, row=3, padx=5, pady=5)
speed_label.grid_remove()  # Скрываем элемент

progress_bar = ttk.Progressbar(frame, mode="determinate", length=300)
progress_bar.grid(column=0, row=4, padx=5, pady=5)
progress_bar.grid_remove()  # Скрываем элемент

# Добавляем кнопку "Скачать Forge"
download_forge_button = ttk.Button(
    frame, text="Скачать Forge", command=download_forge)
download_forge_button.grid(column=0, row=5, padx=5, pady=5, sticky="w")

root.mainloop()
