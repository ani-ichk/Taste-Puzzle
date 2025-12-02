import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QTextEdit, QSpinBox, QComboBox, QLabel,
                             QMessageBox, QFormLayout, QDialog, QListWidget,
                             QListWidgetItem, QDialogButtonBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDoubleSpinBox,
                             QFileDialog, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QIcon
import base64
import io
from PIL import Image, ImageDraw

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


class RecipeDialog(QDialog):
    """Класс диалога для добавления и редактирования рецептов"""

    # Сигнал, испускаемый при сохранении рецепта
    recipe_saved = pyqtSignal()

    def __init__(self, db, user_id, recipe_data=None):
        """Конструктор диалога рецепта"""
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.recipe_data = recipe_data  # Данные рецепта (None для нового рецепта)
        self.ingredients_data = []  # Список для хранения данных ингредиентов
        self.image_data = None  # Данные изображения рецепта

        self.init_ui()
        if self.recipe_data:  # Если переданы данные рецепта (режим редактирования)
            self.load_recipe_data()  # Загрузка данных рецепта в форму

    def format_instructions(self, instructions):
        """Форматирует инструкции с автоматической нумерацией и улучшенным видом"""
        if not instructions:
            return "Инструкции отсутствуют"

        # Разделение инструкций по строкам
        steps = instructions.split('\n')
        numbered_steps = []

        # Нумерация каждого шага
        for i, step in enumerate(steps, 1):
            step = step.strip()
            if step:
                # Убираем существующую нумерацию если есть
                if step and step[0].isdigit() and '.' in step.split()[0]:
                    step = step.split('.', 1)[1].strip()
                numbered_steps.append(f"{i}. {step}")

        if not numbered_steps:
            return "Инструкции отсутствуют"

        return '\n\n'.join(numbered_steps)  # Двойной перенос между шагами

    def unformat_instructions(self, instructions):
        """Убирает автоматическую нумерацию для сохранения в базу"""
        if not instructions:  # Если инструкции пустые
            return ""  # Возвращаем пустую строку

        steps = instructions.split('\n')  # Разделяем инструкции по строкам
        unnumbered_steps = []  # Список для шагов без нумерации

        for step in steps:  # Проходим по всем шагам
            step = step.strip()  # Убираем лишние пробелы
            if step:  # Если шаг не пустой
                # Убираем нумерацию (формат "1. Текст")
                if step[0].isdigit() and '.' in step.split()[0]:
                    step = step.split('.', 1)[1].strip()  # Убираем номер
                unnumbered_steps.append(step)  # Добавляем шаг без номера

        return '\n'.join(unnumbered_steps)  # Возвращаем инструкции без нумерации

    def init_ui(self):
        """Метод инициализации пользовательского интерфейса"""
        layout = QVBoxLayout()  # Создание вертикального компоновщика

        # НАСТРОЙКА ИКОНКИ ОКНА
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(os.path.dirname(current_dir), '..', 'img', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # УСТАНОВКА СТИЛЕЙ ДЛЯ ДИАЛОГА
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #2c3e50;
                font-weight: 500;
            }
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton#image_btn {
                background-color: #95a5a6;
            }
            QPushButton#image_btn:hover {
                background-color: #7f8c8d;
            }
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

        # Прокручиваемая область для длинных форм
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ФОРМА ДЛЯ ОСНОВНОЙ ИНФОРМАЦИИ О РЕЦЕПТЕ
        form_layout = QFormLayout()
        form_layout.setSpacing(12)  # Расстояние между элементами
        form_layout.setContentsMargins(10, 10, 10, 10)  # Отступы

        # Создание элементов ввода
        self.name_input = QLineEdit()  # Поле ввода названия рецепта
        self.name_input.setStyleSheet("font-size: 16px; font-weight: bold;")  # Стиль для названия

        self.description_input = QTextEdit()  # Текстовое поле для описания
        self.description_input.setMaximumHeight(80)  # Ограничение высоты поля

        self.instruction_input = QTextEdit()  # Текстовое поле для инструкций
        self.instruction_input.setMaximumHeight(150)
        self.instruction_input.setPlaceholderText("Каждая новая строка будет автоматически пронумерована")

        self.cook_time_input = QSpinBox()  # Спинбокс для времени приготовления
        self.cook_time_input.setRange(1, 480)  # Установка диапазона значений (1-480 минут)
        self.cook_time_input.setSuffix(' мин')  # Добавление единицы измерения

        # Выпадающий список категорий
        self.category_combo = QComboBox()
        categories = self.db.get_categories()  # Получение категорий из базы данных
        for cat_id, cat_name, cat_type in categories:  # Цикл по всем категориям
            self.category_combo.addItem(cat_name, cat_id)  # Добавление категории в список

        # СЕКЦИЯ ЗАГРУЗКИ ИЗОБРАЖЕНИЯ
        image_layout = QHBoxLayout()
        self.image_label = QLabel()  # Метка для отображения изображения
        self.image_label.setFixedSize(150, 150)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
                background-color: #ecf0f1;
                color: #7f8c8d;
            }
        """)
        self.image_label.setText("Изображение\nне выбрано")  # Текст по умолчанию

        load_image_btn = QPushButton("Выбрать изображение")
        load_image_btn.setObjectName("image_btn")  # Установка имени объекта для стилей
        load_image_btn.clicked.connect(self.load_image)

        image_layout.addWidget(self.image_label)
        image_layout.addWidget(load_image_btn)

        # ДОБАВЛЕНИЕ ЭЛЕМЕНТОВ В ФОРМУ
        form_layout.addRow('Название:', self.name_input)
        form_layout.addRow('Описание:', self.description_input)
        form_layout.addRow('Категория:', self.category_combo)
        form_layout.addRow('Время приготовления:', self.cook_time_input)
        form_layout.addRow('Изображение:', image_layout)  # Добавление секции изображения
        form_layout.addRow('Инструкции:', self.instruction_input)

        # СЕКЦИЯ ДЛЯ РАБОТЫ С ИНГРЕДИЕНТАМИ
        ingredients_layout = QVBoxLayout()
        ingredients_layout.addWidget(QLabel('Ингредиенты:'))

        # Панель добавления ингредиентов
        add_ingredient_layout = QHBoxLayout()

        # Выпадающий список ингредиентов
        self.ingredient_combo = QComboBox()  # Выпадающий список ингредиентов
        ingredients = self.db.get_ingredients()  # Получение ингредиентов из базы
        for ing_id, ing_name in ingredients:
            self.ingredient_combo.addItem(ing_name, ing_id)

        # Спинбокс для количества
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.1, 10000)  # Установка диапазона
        self.quantity_input.setDecimals(2)  # Установка количества знаков после запятой
        self.quantity_input.setValue(100)  # Установка значения по умолчанию
        self.quantity_input.setSingleStep(10)  # Шаг изменения

        # Выпадающий список единиц измерения
        self.unit_combo = QComboBox()
        units = ["г", "кг", "мл", "л", "шт", "ст.л.", "ч.л.", "стакан", "щепотка", "по вкусу"]
        self.unit_combo.addItems(units)  # Добавление единиц в список

        # Кнопка добавления ингредиента
        add_ingredient_btn = QPushButton('Добавить')
        add_ingredient_btn.clicked.connect(self.add_ingredient)

        # Добавление элементов на панель
        add_ingredient_layout.addWidget(QLabel('Ингредиент:'))
        add_ingredient_layout.addWidget(self.ingredient_combo)
        add_ingredient_layout.addWidget(QLabel("Количество:"))
        add_ingredient_layout.addWidget(self.quantity_input)
        add_ingredient_layout.addWidget(self.unit_combo)
        add_ingredient_layout.addWidget(add_ingredient_btn)

        # Создание таблицы для отображения добавленных ингредиентов
        self.ingredients_table = QTableWidget()
        self.ingredients_table.setColumnCount(3)  # Установка количества столбцов
        self.ingredients_table.setHorizontalHeaderLabels(["Ингредиент", "Количество", "Единица"])
        self.ingredients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Кнопка удаления ингредиента
        remove_ingredient_btn = QPushButton('Удалить выбранный')
        remove_ingredient_btn.clicked.connect(self.remove_ingredient)

        # Добавление элементов в секцию ингредиентов
        ingredients_layout.addLayout(add_ingredient_layout)  # Панель добавления
        ingredients_layout.addWidget(self.ingredients_table)  # Таблица ингредиентов
        ingredients_layout.addWidget(remove_ingredient_btn)  # Кнопка удаления

        # СЕКЦИЯ ДЛЯ КБЖУ (ПИЩЕВОЙ ЦЕННОСТИ)
        kbju_layout = QHBoxLayout()
        kbju_layout.addWidget(QLabel('Пищевая ценность:'))  # Заголовок секции

        # Создание элементов для КБЖУ
        self.calories_input = QSpinBox()
        self.calories_input.setRange(0, 5000)  # Установка диапазона
        self.calories_input.setPrefix("Калории: ")  # Добавление префикса
        self.calories_input.setSuffix(" ккал")  # Добавление суффикса

        self.proteins_input = QDoubleSpinBox()  # Спинбокс для белков
        self.proteins_input.setRange(0, 200)
        self.proteins_input.setPrefix("Белки: ")
        self.proteins_input.setSuffix(" г")

        self.fats_input = QDoubleSpinBox()  # Спинбокс для жиров
        self.fats_input.setRange(0, 200)
        self.fats_input.setPrefix("Жиры: ")
        self.fats_input.setSuffix(" г")

        self.carbs_input = QDoubleSpinBox()  # Спинбокс для углеводов
        self.carbs_input.setRange(0, 200)
        self.carbs_input.setPrefix("Углеводы: ")
        self.carbs_input.setSuffix(" г")

        # Добавление элементов КБЖУ в компоновщик
        kbju_layout.addWidget(self.calories_input)
        kbju_layout.addWidget(self.proteins_input)
        kbju_layout.addWidget(self.fats_input)
        kbju_layout.addWidget(self.carbs_input)
        kbju_layout.addStretch()  # Растягиваемое пространство

        # ПАНЕЛЬ КНОПОК УПРАВЛЕНИЯ
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton('Сохранить')  # Кнопка сохранения
        save_btn.clicked.connect(self.save_recipe)
        cancel_btn = QPushButton("Отмена")  # Кнопка отмены
        cancel_btn.clicked.connect(self.reject)  # Подключение обработчика (закрытие диалога)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        # ДОБАВЛЕНИЕ ВСЕХ СЕКЦИЙ В ОСНОВНОЙ КОМПОНОВЩИК (layout)
        scroll_layout.addLayout(form_layout)  # Форма основной информации
        scroll_layout.addLayout(ingredients_layout)  # Секция ингредиентов
        scroll_layout.addLayout(kbju_layout)  # Секция КБЖУ
        scroll_layout.addLayout(buttons_layout)  # Панель кнопок

        scroll_area.setWidget(scroll_widget)  # Установка виджета в область прокрутки
        scroll_area.setWidgetResizable(True)  # Разрешение изменения размера виджета
        layout.addWidget(scroll_area)  # Добавление области прокрутки в основной layout

        self.setLayout(layout)
        # Установка заголовка окна в зависимости от режима
        self.setWindowTitle('Редактировать рецепт' if self.recipe_data else 'Новый рецепт')
        self.resize(800, 700)  # Установка размеров окна

    def load_image(self):
        """Загружает изображение для рецепта"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать изображение",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All files (*)"
        )

        if file_name:
            try:
                # Загружаем изображение и преобразуем в QPixmap для отображения
                pixmap = QPixmap(file_name)
                scaled_pixmap = pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)

                # Сохраняем путь к файлу для базы данных
                self.image_data = file_name  # Храним путь

            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить изображение: {e}")

    def add_ingredient(self):
        """Метод добавления ингредиента в таблицу"""
        try:
            ing_id = self.ingredient_combo.currentData()  # Получение ID выбранного ингредиента
            ing_name = self.ingredient_combo.currentText()  # Получение названия ингредиента
            quantity = self.quantity_input.value()  # Получение количества
            unit = self.unit_combo.currentText()  # Получение единицы измерения

            # Проверка количества
            if quantity <= 0:
                QMessageBox.warning(self, 'Ошибка', 'Введите количество больше 0')
                return

            # Проверка на дубликаты
            for existing_ing in self.ingredients_data:
                if existing_ing[0] == ing_id:  # Если ингредиент уже добавлен
                    QMessageBox.warning(self, 'Ошибка', 'Этот ингредиент уже добавлен')
                    return

            # Добавление ингредиента в данные (ID, количество, единица)
            self.ingredients_data.append((ing_id, quantity, unit))

            # Добавление ингредиента в таблицу
            row = self.ingredients_table.rowCount()  # Получение текущего количества строк
            self.ingredients_table.insertRow(row)  # Вставка новой строки
            self.ingredients_table.setItem(row, 0, QTableWidgetItem(ing_name))  # Название ингредиента
            self.ingredients_table.setItem(row, 1, QTableWidgetItem(str(quantity)))  # Количество
            self.ingredients_table.setItem(row, 2, QTableWidgetItem(unit))  # Единица измерения

            # Очистка полей ввода
            self.quantity_input.setValue(100)  # Сброс количества к значению по умолчанию

        except Exception as e:
            print(f"Ошибка при добавлении ингредиента: {e}")
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при добавлении ингредиента: {e}')

    def remove_ingredient(self):
        """Метод удаления выбранного ингредиента из таблицы"""
        try:
            current_row = self.ingredients_table.currentRow()  # Получение индекса текущей строки
            if current_row >= 0:  # Если строка выбрана
                self.ingredients_data.pop(current_row)  # Удаление данных ингредиента из списка
                self.ingredients_table.removeRow(current_row)  # Удаление строки из таблицы
            else:
                QMessageBox.warning(self, 'Ошибка', 'Выберите ингредиент для удаления')
        except Exception as e:
            print(f"Ошибка при удалении ингредиента: {e}")
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при удалении ингредиента: {e}')

    def load_recipe_data(self):
        """Метод загрузки данных рецепта в форму (для редактирования)"""
        try:
            # Загрузка основных данных рецепта
            self.name_input.setText(self.recipe_data[2])  # Установка названия
            self.description_input.setPlainText(self.recipe_data[4] or '')  # Установка описания

            # Форматируем инструкции с автоматической нумерацией
            instructions = self.format_instructions(self.recipe_data[3])
            self.instruction_input.setPlainText(instructions)  # Установка инструкций

            self.cook_time_input.setValue(self.recipe_data[8] or 30)  # Установка времени приготовления

            # Установка категории
            category_index = self.category_combo.findData(self.recipe_data[5])  # Поиск индекса категории по ID
            if category_index >= 0:  # Если категория найдена
                self.category_combo.setCurrentIndex(category_index)  # Установка текущей категории

            # Загрузка изображения если есть
            if self.recipe_data[6]:  # image data
                # Получаем QPixmap из базы данных
                pixmap = self.db.get_recipe_image(self.recipe_data[0])
                if pixmap and not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
                    self.image_label.setPixmap(scaled_pixmap)
                    # Сохраняем текущий путь к изображению
                    self.image_data = self.recipe_data[6]
                else:
                    # Если не удалось загрузить изображение, устанавливаем текстовую метку
                    self.image_label.setText("Изображение\nне загружено")
                    self.image_label.setStyleSheet(self.image_label.styleSheet() + "color: #6c757d; font-size: 10px;")

            # Загрузка ингредиентов рецепта
            ingredients = self.db.get_recipe_ingredients(self.recipe_data[0])
            for ing_name, quantity, unit in ingredients:
                # Поиск ID ингредиента по названию
                ing_id = None
                for i_id, i_name in self.db.get_ingredients():
                    if i_name == ing_name:  # Если название совпадает
                        ing_id = i_id  # Сохранение ID
                        break

                if ing_id is not None:  # Если ID найден
                    self.ingredients_data.append((ing_id, quantity, unit))  # Добавление в данные

                    # Добавление в таблицу
                    row = self.ingredients_table.rowCount()
                    self.ingredients_table.insertRow(row)
                    self.ingredients_table.setItem(row, 0, QTableWidgetItem(ing_name))
                    self.ingredients_table.setItem(row, 1, QTableWidgetItem(str(quantity)))
                    self.ingredients_table.setItem(row, 2, QTableWidgetItem(unit))

            # Загрузка данных КБЖУ
            if self.recipe_data[11]:  # калории
                self.calories_input.setValue(self.recipe_data[11])
            if self.recipe_data[12]:  # белки
                self.proteins_input.setValue(self.recipe_data[12])
            if self.recipe_data[13]:  # жиры
                self.fats_input.setValue(self.recipe_data[13])
            if self.recipe_data[14]:  # углеводы
                self.carbs_input.setValue(self.recipe_data[14])

        except Exception as e:
            print(f"Ошибка при загрузке данных рецепта: {e}")
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при загрузке данных рецепта: {e}')

    def save_recipe(self):
        """Метод сохранения рецепта"""
        try:
            # Проверка обязательных полей
            if not self.name_input.text().strip():  # Если название пустое
                QMessageBox.warning(self, 'Ошибка', 'Введите название рецепта')
                return

            if not self.ingredients_data:  # Если нет ингредиентов
                QMessageBox.warning(self, 'Ошибка', 'Добавьте хотя бы один ингредиент')
                return

            # Получение данных из формы
            category_id = self.category_combo.currentData()  # ID выбранной категории

            # Убираем автоматическую нумерацию перед сохранением
            instructions = self.unformat_instructions(self.instruction_input.toPlainText())

            nutrition_data = (  # Данные КБЖУ
                self.calories_input.value(),
                self.proteins_input.value(),
                self.fats_input.value(),
                self.carbs_input.value()
            )

            # Сохранение рецепта в базу данных
            if self.recipe_data:  # Если это редактирование существующего рецепта
                success = self.db.update_recipe(
                    self.recipe_data[0],  # ID рецепта
                    self.name_input.text(),  # Название
                    instructions,  # Инструкции
                    self.description_input.toPlainText(),  # Описание
                    category_id,  # ID категории
                    self.cook_time_input.value(),  # Время приготовления
                    self.ingredients_data,  # Список ингредиентов
                    nutrition_data,  # Данные КБЖУ
                    self.image_data  # Данные изображения
                )
            else:  # Если это создание нового рецепта
                recipe_id = self.db.add_recipe(
                    self.user_id,
                    self.name_input.text(),
                    instructions,
                    self.description_input.toPlainText(),
                    category_id,
                    self.cook_time_input.value(),
                    self.ingredients_data,
                    nutrition_data,
                    self.image_data
                )
                success = recipe_id is not None

            if success:
                self.recipe_saved.emit()  # Испускание сигнала о сохранении рецепта
                self.accept()  # Закрытие диалога с положительным результатом
            else:
                QMessageBox.warning(self, 'Ошибка', 'Не удалось сохранить рецепт')

        except Exception as e:
            print(f"Ошибка при сохранении рецепта: {e}")
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при сохранении рецепта: {e}')


class RecipeCardDialog(QDialog):
    """Класс диалога для просмотра рецепта в виде карточки"""
    # Сигналы для обновления, удаления и добавления в корзину
    recipe_updated = pyqtSignal()
    recipe_deleted = pyqtSignal(int)  # (передаем ID)
    add_to_cart = pyqtSignal(list)

    def __init__(self, recipe_data, db, user_id):
        super().__init__()
        self.recipe_data = recipe_data
        self.db = db
        self.user_id = user_id
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(650, 900)
        self.setWindowTitle(self.recipe_data[2])
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef);
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #2c3e50;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton {
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 20px;
                margin: 5px;
                border: none;
                min-width: 60px;
                min-height: 60px;
            }
            QPushButton:hover {
                transform: scale(1.05);
            }
            QPushButton:pressed {
                transform: scale(0.95);
            }
            QPushButton#cart_btn {
                background-color: #28a745;
                color: white;
            }
            QPushButton#cart_btn:hover {
                background-color: #218838;
            }
            QPushButton#favorite_btn {
                background-color: #ffc107;
                color: #212529;
            }
            QPushButton#favorite_btn:hover {
                background-color: #e0a800;
            }
            QPushButton#cooked_btn {
                background-color: #17a2b8;
                color: white;
            }
            QPushButton#cooked_btn:hover {
                background-color: #138496;
            }
            QPushButton#edit_btn {
                background-color: #007bff;
                color: white;
            }
            QPushButton#edit_btn:hover {
                background-color: #0056b3;
            }
            QPushButton#delete_btn {
                background-color: #dc3545;
                color: white;
            }
            QPushButton#delete_btn:hover {
                background-color: #c82333;
            }
            .section-header {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-top: 25px;
                margin-bottom: 10px;
                padding: 5px;
                background-color: white;
                border-radius: 6px;
                border-left: 4px solid #007bff;
            }
            .info-box {
                background-color: white;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                margin: 5px 0;
            }
        """)

        # Основной layout с прокруткой
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # === ПЕРВЫЙ БЛОК: Заголовок и основная информация ===

        # Название рецепта по центру
        title = QLabel(self.recipe_data[2])
        title.setStyleSheet("""
            QLabel {
                font-size: 26px;
                font-weight: bold;
                color: #2c3e50;
                padding: 20px;
                background-color: white;
                border-radius: 10px;
                text-align: center;
                border: 2px solid #dee2e6;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        # Блок с фото и информацией
        first_block_layout = QHBoxLayout()
        first_block_layout.setSpacing(20)

        # Фотография (слева) - занимает 40% ширины
        image_container = QVBoxLayout()
        image_label = QLabel()
        image_label.setFixedSize(220, 180)  # Уменьшаем немного для баланса
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 10px;
            }
        """)

        # Загрузка изображения
        pixmap = self.db.get_recipe_image(self.recipe_data[0])
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(210, 170, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
        else:
            image_label.setText("🖼️\nНет\nизображения")
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setStyleSheet(image_label.styleSheet() + "color: #6c757d; font-size: 12px;")

        image_container.addWidget(image_label)
        image_container.addStretch()

        # Информация справа (категория и время) - занимает 60% ширины
        info_container = QVBoxLayout()
        info_container.setSpacing(15)

        # Категория
        category_box = QWidget()
        category_box.setStyleSheet("""
            QWidget {
                background-color: #e3f2fd;
                border-radius: 8px;
                border: 1px solid #bbdefb;
            }
        """)
        category_layout = QVBoxLayout(category_box)
        category_label = QLabel("🍽️ Категория")
        category_label.setStyleSheet("font-weight: bold; color: #1565c0; font-size: 14px; margin-bottom: 5px;")
        category_value = QLabel(self.recipe_data[9] or 'Не указана')
        category_value.setStyleSheet("color: #1565c0; font-size: 16px; font-weight: 500;")
        category_value.setWordWrap(True)
        category_layout.addWidget(category_label)
        category_layout.addWidget(category_value)

        # Время приготовления
        time_box = QWidget()
        time_box.setStyleSheet("""
            QWidget {
                background-color: #fff3e0;
                border-radius: 8px;
                border: 1px solid #ffe0b2;
            }
        """)
        time_layout = QVBoxLayout(time_box)
        time_label = QLabel("⏱️ Время приготовления")
        time_label.setStyleSheet("font-weight: bold; color: #ef6c00; font-size: 14px; margin-bottom: 5px;")
        time_value = QLabel(f"{self.recipe_data[8] or 'Не указано'} минут")
        time_value.setStyleSheet("color: #ef6c00; font-size: 16px; font-weight: 500;")
        time_layout.addWidget(time_label)
        time_layout.addWidget(time_value)

        # Видео-ссылка если есть
        if self.recipe_data[7]:
            video_box = QWidget()
            video_box.setStyleSheet("""
                QWidget {
                    background-color: #f3e5f5;
                    border-radius: 8px;
                    border: 1px solid #e1bee7;
                }
            """)
            video_layout = QVBoxLayout(video_box)
            video_label = QLabel("🎬 Видео-рецепт")
            video_label.setStyleSheet("font-weight: bold; color: #7b1fa2; font-size: 14px; margin-bottom: 5px;")
            video_link = QLabel(
                f'<a href="{self.recipe_data[7]}" style="color: #7b1fa2; text-decoration: none; font-size: 14px;">Смотреть видео</a>')
            video_link.setOpenExternalLinks(True)
            video_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            video_layout.addWidget(video_label)
            video_layout.addWidget(video_link)
            info_container.addWidget(video_box)

        info_container.addWidget(category_box)
        info_container.addWidget(time_box)
        info_container.addStretch()

        first_block_layout.addLayout(image_container)
        first_block_layout.addLayout(info_container)
        layout.addLayout(first_block_layout)

        # Отступ между блоками
        layout.addSpacing(10)

        # === ВТОРОЙ БЛОК: Описание ===
        if self.recipe_data[4]:
            description_label = QLabel("📝 Описание")
            description_label.setProperty("class", "section-header")
            layout.addWidget(description_label)

            description = QTextEdit()
            description.setPlainText(self.recipe_data[4])
            description.setReadOnly(True)
            description.setFixedHeight(100)
            description.setStyleSheet("""
                QTextEdit {
                    font-size: 14px; 
                    color: #495057; 
                    padding: 15px;
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    line-height: 1.4;
                }
            """)
            layout.addWidget(description)

        # === ТРЕТИЙ БЛОК: Ингредиенты ===
        ingredients_label = QLabel("🛒 Ингредиенты")
        ingredients_label.setProperty("class", "section-header")
        layout.addWidget(ingredients_label)

        ingredients_text = QTextEdit()
        ingredients_text.setReadOnly(True)
        ingredients_text.setFixedHeight(150)
        ingredients_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)

        try:
            ingredients = self.db.get_recipe_ingredients(self.recipe_data[0])
            ingredients_list = ""
            for name, quantity, unit in ingredients:
                ingredients_list += f"• {name}: {quantity} {unit}\n"
            ingredients_text.setPlainText(ingredients_list)
        except Exception as e:
            print(f"Ошибка при загрузке ингредиентов: {e}")
            ingredients_text.setPlainText("Не удалось загрузить ингредиенты")

        layout.addWidget(ingredients_text)

        # === ЧЕТВЕРТЫЙ БЛОК: Инструкции ===
        instructions_label = QLabel("📋 Инструкции")
        instructions_label.setProperty("class", "section-header")
        layout.addWidget(instructions_label)

        instructions_text = QTextEdit()
        instructions_text.setReadOnly(True)
        instructions_text.setFixedHeight(200)
        instructions_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)

        formatted_instructions = self.format_instructions(self.recipe_data[3])
        instructions_text.setPlainText(formatted_instructions)
        layout.addWidget(instructions_text)

        # === ПЯТЫЙ БЛОК: Кнопки действий ===
        buttons_label = QLabel("⚡ Действия")
        buttons_label.setProperty("class", "section-header")
        layout.addWidget(buttons_label)

        # Создаем контейнер для кнопок
        buttons_container = QWidget()
        buttons_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid #dee2e6;
            }
        """)

        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(15)
        buttons_layout.setContentsMargins(20, 10, 20, 10)

        # Кнопка редактирования
        edit_btn = QPushButton("✏️")
        edit_btn.setObjectName("edit_btn")
        edit_btn.setToolTip("Редактировать рецепт")
        edit_btn.setFixedSize(70, 70)
        edit_btn.clicked.connect(self.edit_recipe)

        # Кнопка добавления в корзину
        add_to_cart_btn = QPushButton("🛒")
        add_to_cart_btn.setObjectName("cart_btn")
        add_to_cart_btn.setToolTip("Добавить ингредиенты в корзину")
        add_to_cart_btn.setFixedSize(70, 70)
        add_to_cart_btn.clicked.connect(self.on_add_to_cart)

        # Кнопка удаления
        delete_btn = QPushButton("🗑️")
        delete_btn.setObjectName("delete_btn")
        delete_btn.setToolTip("Удалить рецепт")
        delete_btn.setFixedSize(70, 70)
        delete_btn.clicked.connect(self.delete_recipe)

        # Кнопка избранного
        is_favorite = self.db.is_recipe_favorite(self.user_id, self.recipe_data[0])
        favorite_icon = "💔" if is_favorite else "❤️"
        self.favorite_btn = QPushButton(favorite_icon)
        self.favorite_btn.setObjectName("favorite_btn")
        self.favorite_btn.setToolTip("Убрать из избранного" if is_favorite else "Добавить в избранное")
        self.favorite_btn.setFixedSize(70, 70)
        self.favorite_btn.clicked.connect(self.toggle_favorite)

        # Кнопка отметки приготовления
        is_cooked = self.db.is_recipe_cooked(self.user_id, self.recipe_data[0])
        cooked_icon = "✅" if is_cooked else "⏳"
        self.cooked_btn = QPushButton(cooked_icon)
        self.cooked_btn.setObjectName("cooked_btn")
        self.cooked_btn.setToolTip("Снять отметку приготовления" if is_cooked else "Отметить как приготовленное")
        self.cooked_btn.setFixedSize(70, 70)
        self.cooked_btn.clicked.connect(self.toggle_cooked_status)

        # Равномерно распределяем кнопки
        buttons_layout.addStretch()
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(add_to_cart_btn)
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addWidget(self.favorite_btn)
        buttons_layout.addWidget(self.cooked_btn)
        buttons_layout.addStretch()

        layout.addWidget(buttons_container)
        layout.addStretch()

        # Устанавливаем content_widget в scroll area
        scroll.setWidget(content_widget)

        # Основной layout диалога
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def edit_recipe(self):
        """Открывает диалог редактирования рецепта"""
        try:
            # Создаем диалог напрямую, так как оба класса в одном файле
            dialog = RecipeDialog(self.db, self.user_id, self.recipe_data)
            dialog.recipe_saved.connect(self.recipe_updated)
            dialog.exec()
            self.close()  # Закрываем карточку после редактирования
        except Exception as e:
            print(f"Ошибка при открытии редактора рецепта: {e}")

    def delete_recipe(self):
        """Удаляет рецепт после подтверждения"""
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы действительно хотите удалить этот рецепт?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.db.delete_recipe(self.recipe_data[0])
                if success:
                    self.recipe_deleted.emit(self.recipe_data[0])
                    self.close()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить рецепт")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении рецепта: {e}")

    def format_instructions(self, instructions):
        """Форматирует инструкции с автоматической нумерацией и улучшенным видом"""
        if not instructions:
            return "Инструкции отсутствуют"

        steps = instructions.split('\n')
        numbered_steps = []

        for i, step in enumerate(steps, 1):
            step = step.strip()
            if step:
                # Убираем существующую нумерацию если есть
                if step and step[0].isdigit() and '.' in step.split()[0]:
                    step = step.split('.', 1)[1].strip()
                numbered_steps.append(f"{i}. {step}")

        if not numbered_steps:
            return "Инструкции отсутствуют"

        return '\n\n'.join(numbered_steps)  # Двойной перенос между шагами

    def on_add_to_cart(self):
        """Добавляет ингредиенты рецепта в корзину"""
        try:
            ingredients = self.db.get_recipe_ingredients(self.recipe_data[0])
            self.add_to_cart.emit(ingredients)
            QMessageBox.information(self, "Успех", "Ингредиенты добавлены в корзину!")
        except Exception as e:
            print(f"Ошибка при добавлении в корзину: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось добавить ингредиенты в корзину")

    def toggle_favorite(self):
        """Добавляет или убирает рецепт из избранного"""
        try:
            success = self.db.toggle_favorite(self.user_id, self.recipe_data[0])
            if success:
                is_favorite = self.db.is_recipe_favorite(self.user_id, self.recipe_data[0])
                favorite_icon = "❤️" if is_favorite else "🤍"
                tooltip = "Убрать из избранного" if is_favorite else "Добавить в избранное"

                self.favorite_btn.setText(favorite_icon)
                self.favorite_btn.setToolTip(tooltip)
                self.recipe_updated.emit()

                # Показываем сообщение о действии
                action = "добавлен в" if is_favorite else "удален из"
                QMessageBox.information(self, "Избранное",
                                        f"Рецепт '{self.recipe_data[2]}' {action} избранное!")
        except Exception as e:
            print(f"Ошибка при переключении избранного: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить статус избранного")

    def toggle_cooked_status(self):
        """Переключает статус приготовления рецепта"""
        try:
            current_status = self.db.is_recipe_cooked(self.user_id, self.recipe_data[0])
            success = self.db.mark_recipe_as_cooked(self.user_id, self.recipe_data[0], not current_status)

            if success:
                new_status = not current_status
                cooked_icon = "✅" if new_status else "⏳"
                tooltip = "Снять отметку приготовления" if new_status else "Отметить как приготовленное"

                self.cooked_btn.setText(cooked_icon)
                self.cooked_btn.setToolTip(tooltip)
                self.recipe_updated.emit()

                # Показываем сообщение о действии
                action = "отмечен как приготовленный" if new_status else "снята отметка приготовления"
                QMessageBox.information(self, "Приготовлено",
                                        f"Рецепт '{self.recipe_data[2]}' {action}!")
        except Exception as e:
            print(f"Ошибка при изменении статуса приготовления: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить статус приготовления")
