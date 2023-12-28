import hashlib, os, ctypes, shutil, uuid
from ctypes import wintypes
from tqdm import tqdm  # добавлен импорт

# Определение структуры для BROWSEINFO
class BROWSEINFO(ctypes.Structure):
	_fields_ = [
		("hwndOwner", wintypes.HWND),
		("pidlRoot", ctypes.POINTER(ctypes.c_void_p)),
		("pszDisplayName", ctypes.c_char_p),
		("lpszTitle", ctypes.c_char_p),
		("ulFlags", wintypes.UINT),
		("lpfn", ctypes.c_void_p),
		("lParam", wintypes.LPARAM),
		("iImage", wintypes.INT)
	]

# Получение указателя на функцию SHBrowseForFolder
shell32 = ctypes.windll.shell32
shBrowseForFolder = shell32.SHBrowseForFolder
shBrowseForFolder.argtypes = [ctypes.POINTER(BROWSEINFO)]
shBrowseForFolder.restype = ctypes.c_void_p

# Получение указателя на функцию SHGetPathFromIDList
shGetPathFromIDList = shell32.SHGetPathFromIDList
shGetPathFromIDList.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
shGetPathFromIDList.restype = wintypes.BOOL

last_folder = None

def calculate_hash(file_path):
	"""Вычисляет хэш файла."""
	hasher = hashlib.sha256()
	with open(file_path, 'rb') as f:
		while chunk := f.read(8192):
			hasher.update(chunk)
	return hasher.hexdigest()

def get_files_in_folder(folder_path):
	"""Возвращает список файлов в указанной папке."""
	files = []
	for file_name in os.listdir(folder_path):
		file_path = os.path.join(folder_path, file_name)
		if os.path.isfile(file_path):
			files.append(file_path)
	return files

def compare_and_copy_files(src_folder, dest_folder):
	"""Сравнивает хэши файлов из двух папок и копирует те, которых нет в dest_folder."""
	src_files = get_files_in_folder(src_folder)
	dest_files = get_files_in_folder(dest_folder)
	src_hashes = [calculate_hash(file_path) for file_path in src_files]
	unique_prefix = str(uuid.uuid4())

	for i, file_path in enumerate(tqdm(dest_files, desc="Сравнение и копирование файлов", unit="файл")):
		file_hash = calculate_hash(file_path)
		if file_hash not in src_hashes:
			new_filename = f"{unique_prefix}_{i}.{file_path.split('.')[-1]}"
			src_folder_path = os.path.join(src_folder, new_filename)
			shutil.copy(file_path, src_folder_path)

def path_to_pidl(path):
	pidl = ctypes.POINTER(ctypes.c_void_p)()
	shell32.SHParseDisplayName(path, 0, ctypes.byref(pidl), 0, 0)
	return pidl

def select_folder(lpszTitle):
	global last_folder
	 # Инициализация BROWSEINFO
	bi = BROWSEINFO()
	bi.hwndOwner = 0
	bi.pidlRoot = ctypes.POINTER(ctypes.c_void_p)() if last_folder is None else path_to_pidl('\\'.join(last_folder.split('\\')[:-1]))
	bi.pszDisplayName = ctypes.cast(ctypes.create_string_buffer(260), ctypes.c_char_p)
	bi.lpszTitle = lpszTitle.encode('cp1251')
	bi.ulFlags = 0x00000001  # BIF_RETURNONLYFSDIRS
	bi.lpfn = 0
	bi.lParam = 0
	bi.iImage = 0

	# Вызов SHBrowseForFolder
	pidl = shBrowseForFolder(ctypes.byref(bi))

	# Получение пути из pidl
	path = ctypes.create_string_buffer(260)
	shGetPathFromIDList(pidl, path)

	last_folder = path.value.decode('utf-8')

	return last_folder

def ask_repeat():
	"""Спрашивает пользователя, хочет ли он повторить процесс."""
	return ctypes.windll.user32.MessageBoxW(0, "Хотите повторить процесс?", "Повторить процесс", 1) == 1

if __name__ == "__main__":
	repeat_process = True

	while repeat_process:
		folder1_path = select_folder("Выберите первую папку:")

		folder2_path = select_folder("Выберите вторую папку:")

		if os.path.exists(folder1_path) and os.path.exists(folder2_path):
			compare_and_copy_files(folder1_path, folder2_path)
			print("Процесс завершен: файлы скопированы.")
		else:
			print("Одна или обе папки не найдены.")

		repeat_process = ask_repeat()